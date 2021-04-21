"""
``simpcli3``
======================

A Python3 module for turning functions into cmd-line programs trivially.

Features
--------

Features marked with a ✓ are currently implemented; features marked with a ⊘
are not yet implemented.

- [✓] Positional arguments
- [✓] Boolean flags
- [✓] Integer, string, float, and other simple types as arguments
- [✓] Default values
- [✓] Arguments with a finite set of choices
- [⊘] Subcommands
- [⊘] Mutually exclusive groups
- [⊘] Compositon in dataclasses

Examples
--------

A simple parser with flags:

.. code-block:: pycon

    from simpcli3 import CliApp
    from typing import List

    def myls(paths: List[str], exclude: List[str]=[], mystr: str=None, follow_symlinks: bool=False):
        print(f"Received args: {paths}\n")
        for path in paths:
            print(path)

    if __name__ == "__main__":
        CliApp(myls).run()

Using defaults:

.. code-block:: pycon

    from dataclasses import dataclass, field
    from enum import Enum
    from typing import List

    class PrintFormat(Enum):
        LINE_PER_ENTRY = 1
        PRETTY = 2

    @dataclass
    class ListDirectoryArgs:
        paths: List[str] = field(metadata=dict(positional=True))
        exclude: List[str] = field(default_factory=list)
        print_format: PrintFormat = PrintFormat.PRETTY
        follow_symlinks: bool = True

    def myls(lsargs: ListDirectoryArgs):
        print(f"Received args: {lsargs}\n")
        for path in lsargs.paths:
            print(path)

    if __name__ == "__main__":
        from simpcli3 import CliApp
        CliApp(myls).run()


License
-------

MIT License

Copyright (c) 2020 Michael V. DePalatis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import argparse
from contextlib import suppress
from dataclasses import is_dataclass, MISSING, fields
from enum import Enum
from typing import TypeVar, List, Dict, Callable, Optional

from gettext import gettext as _
from argparse import ArgumentError

from .logging import logger
from .docstring import get_attribute_docstring

__version__ = "0.0.3"

OptionsType = TypeVar("OptionsType")


class ArgumentParser(argparse.ArgumentParser):
    """Command line argument parser that derives its options from a dataclass.

    Parameters
    ----------
    options_class
        The dataclass that defines the options.
    args, kwargs
        Passed along to :class:`argparse.ArgumentParser`.

    """

    def __init__(
            self,
            options_class: OptionsType,
            *,
            auto_deplural: bool = True,
            expand_dataclass_arg: bool = False,
            **kwargs):
        kwargs = self._opinionated_defaults(kwargs)
        super().__init__(**kwargs)
        self._options_type: OptionsType = options_class
        self._posarg_stored_as: Dict = {}
        self._auto_deplural = auto_deplural
        self.expand_dataclass_arg = expand_dataclass_arg
        self._used_flagnames = []
        self._dicts = []

        if self._options_type:
            self._add_dataclass_options(self._options_type)
        
        # hack to avoid having to decorate the passed-in function to make it accept uniform interface.
        # TODO Rule out adding a runtime attribute on the function, I think this doesn't work in certain interpreters.
    def _opinionated_defaults(self, kwargs):
        from argparse import RawTextHelpFormatter
        defaults = {
            'allow_abbrev': False,
            'formatter_class': RawTextHelpFormatter,
        }
        returning = kwargs.copy()
        for key, val in defaults.items():
            if key not in kwargs:
                returning[key] = val
        return returning
    
    def _determine_flagname(self, maybe_prefix, param_name, repeated):
        if repeated and len(param_name) > 3 and param_name.endswith('s'):
            param_name = param_name[:-1]  # remove last s, that is e.g. GccArgs.excludes becomes --exclude
        flagname = f"{param_name.strip('_').replace('_', '-')}"
        if flagname in self._used_flagnames:
            # TODO Perhaps take some wisdom from SimpleParser "resolve" code.
            # It is clear that in the test case with CommonArgs.version, we could prefix ca. on the priorly-
            # -assigned no prefix arg. And we can't just reorder because there is no default for CommonArgs member,
            # while there is for version. So, we need to resolve flag names _first_ across the dataclass
            # before calling add_arguments.
            # This refactor seems as good a time as any to switch to the boolean matrix implementation style.
            assert maybe_prefix, f"{flagname} was not a unique flag, generated by param_name={param_name}"
            return self._determine_flagname(None, maybe_prefix + '.' + flagname, repeated)
        self._used_flagnames.append(flagname)
        return flagname

    def _determine_flags(self, flagname, param_name, positional, short_flag):
        if not positional:
            returning = []
            if short_flag:
                # Can pass either True or e.g. '-o'
                if short_flag is True:
                    returning.append(f'-{param_name[0]}')
                else:
                    returning.append(short_flag)
            returning.append(f"--{flagname}")
            return returning
        else:
            return [f'{flagname}']

    def _disable_flags(self, flagname):
        return [f"--no-{flagname}"]

    def _elem_type(self, thetype):
        # TODO Test coverage of this.
        try:
            elem_type = thetype.__args__[0]
            return elem_type, True
        except Exception:
            return thetype, False

    def _get_enum_parser(self, enum_type):
        def parse_enum(val):
            # I have no idea why they chose this syntax for parsing a string.
            return enum_type[val]
        return parse_enum

    def _check_value(self, action, value):
        """In order to prevent --help from showing choices as EnumType.VALUE,
        thus leading user into typing wrong value,
        we need to replace original ArgumentParser functionality here,
        because it checks for existence in list of defaults _after_ converting to enum type,
        although list of defaults is given as strings."""
        # converted value must be one of the choices (if specified)
        if action.choices is None:
            return
        enum_choices = []
        for str_val in action.choices:
            try:
                enum_choices.append(action.type(str_val))
            except Exception:  # Naughty to have an option in choices which doesn't parse into your type...
                pass

        # Replace action.choices with enum_choices in the original implementation and carry on:
        if value not in enum_choices:
            args = {'value': value,
                    'choices': ', '.join(map(repr, action.choices))}
            msg = _('invalid choice: %(value)r (choose from %(choices)s)')
            raise ArgumentError(action, msg % args)

    def _check_gotchas(self, field):
        if isinstance(field.type, Field):
            raise ValueError(f"Did you do '{field.name}: field(...' rather than {field.name}: SomeType = field(...'?")

    def _get_help(self, options_type, field):
        if 'help' in field.metadata:
            return field.metadata['help']
        try:
            v = get_attribute_docstring(options_type, field.name)
            return v.comment_below or v.comment_above or v.comment_inline or None 
        except Exception:
            return None
        
    def _add_dataclass_options(self, options_type, prefix=None) -> None:
        if not is_dataclass(options_type):
            raise TypeError(f"cls must be a dataclass, but given {self._options_type}")

        logger.debug(f"{fields(options_type)}")
        for field in fields(options_type):
            if not field.metadata.get("cmdline", True):
                continue
            self._check_gotchas(field)
            elem_type, repeated = self._elem_type(field.type)
            flagname = self._determine_flagname(prefix, field.name, repeated)
            positional = (('args' in field.metadata and not field.metadata['args'][0].startswith('-'))
                or bool(field.metadata.get('positional')))
            short_flag = field.metadata.get('short_flag')
            if positional and short_flag:
                raise ValueError("Can't have a positional argument with a flag.")
            args = field.metadata.get("args", self._determine_flags(flagname, field.name, positional, short_flag))
            if positional:
                self._posarg_stored_as[args[0]] = field.name

            if is_dataclass(elem_type):
                # TODO Strategy:
                #   1. BFS and include all of the flags. Consider the case of a list of dataclass instances as a field.
                #   2. Also consider conflict resolution.
                msg = ("Cannot currently handle composition of dataclasses." +
                        "You could try inheritance, or add support yourself.")
                raise NotImplementedError(msg)
                # self._add_dataclass_options(elem_type, prefix=field.name)
                # continue
            kwargs = {
                "type": elem_type,
                "help": self._get_help(options_type, field),
            }

            # We want to ensure that we store the argument based on the
            # name of the field and not whatever flag name was provided
            if not positional:
                # For some reason argparse doesn't like a different dest for a positional arg.
                kwargs["dest"] = field.name

            if field.metadata.get("choices") is not None:
                kwargs["choices"] = field.metadata["choices"]
            elif issubclass(getattr(field.type, '__origin__', object), Dict):
                key_type, val_type = field.type.__args__
                if not key_type is str:
                    raise ValueError("Unsupported keytype: {}".format(key_type))
                repeated = True
                # TODO Pass it through argparse as string, transform / parse it ourselves?
                # # No wonder invoke made  their own parser.
                def get_parser(vtype):
                    def parser(item):
                        if '=' not in item:
                            raise ValueError("expected format key=value, received: {!r}".format(item))
                        k, v = item.split('=')
                        return k, vtype(v)
                    return parser
                kwargs["type"] = get_parser(val_type)
                self._dicts.append(field.name)
            elif issubclass(elem_type, Enum):
                kwargs["choices"] = [elem.name for elem in elem_type]
                # kwargs["choices"] = [elem for elem in elem_type]  # worked, but help wasn't as pretty.

            if (field.default is MISSING) and (field.default_factory is MISSING) and not positional:
                kwargs["required"] = True
            else:
                if field.default_factory is not MISSING:
                    kwargs["default"] = field.default_factory()
                    logger.debug(f"Set default for {field.name} to {kwargs['default']}")
                else:

                    def determine_default(field):
                        # Only if not required:
                        if field.default is MISSING and repeated:
                            return []
                        return field.default

                    kwargs["default"] = determine_default(field)
                    #  if kwargs.get("default") is MISSING:
                    #     kwargs["default"] = None

                # if isinstance(kwargs["default"], Enum):
                #   kwargs["default"] = kwargs["default"].name
                    # TODO default here need to change if repeated?

            if field.type is bool:
                if field.default:
                    kwargs["action"] = "store_false"
                    args = field.metadata.get("args", self._disable_flags(flagname))
                else:
                    kwargs["action"] = "store_true"
                
                for key in ("type", "required", "default"):
                    with suppress(KeyError):
                        kwargs.pop(key)
            if repeated:
                if not positional:
                    kwargs["action"] = "append"
                else:
                    kwargs['nargs'] = '*'
            if not repeated and positional:
                kwargs['nargs'] = '?'

            if issubclass(elem_type, Enum):
                kwargs["type"] = self._get_enum_parser(elem_type)
                if kwargs["default"] is not MISSING and isinstance(kwargs["default"], Enum):
                    kwargs["default"] = kwargs["default"].name

            if "store" not in kwargs.get("action", '') and not issubclass(elem_type, Enum):
                kwargs['metavar'] = elem_type.__name__

            logger.debug(f"add_argument: {args} {kwargs}. positional={positional}")
            self.add_argument(*args, **kwargs)

    def _handle_empty_posarg(self, ns_dict):
        if not self._posarg_stored_as:
            return
        to_remove = []
        # Necessary because we can't use 'dest' with positional args.
        for dict_key, dataclass_key in self._posarg_stored_as.items():
            if dict_key != dataclass_key:
                ns_dict[dataclass_key] = ns_dict[dict_key]
                to_remove.append(dict_key)
        for dict_key in to_remove:
            ns_dict.pop(dict_key)
        # Can't create a dataclass without providing a all args unless they have defaults.
        # In the case of a positional arg without default, we will have arg_name=MISSING here,
        # rather than the arg not being provided, which dataclass accepts as the value without question.
        # bool(MISSING()) == True, so can't expect user to guard against with "if not myargs.posarg".
        # It is tempting to raise an argparsing error here. But the ideal solution seems to be to pass [].
        # This way, if the user prefers that an empty list isn't a valid argument, they can raise the TypeError themselves,
        # And this also prevents other Python functions calling into the user's function with an empty list.
        # ns_dict[self._posarg_name] = []

    def _handle_missing(self, ns_dict):
        to_remove = {k for k, v in ns_dict.items() if v is MISSING}
        for key in to_remove:
            ns_dict.pop(key)

    def _handle_dicts(self, ns_dict):
        for name in self._dicts:
            if name not in ns_dict:
                continue
            ns_dict[name] = dict(ns_dict[name])

    def parse_args(self, *args, **kwargs) -> OptionsType:
        """Parse arguments and return as the dataclass type."""
        namespace = super().parse_args(*args, **kwargs)
        ns_dict = vars(namespace)
        self._handle_empty_posarg(ns_dict)
        self._handle_missing(ns_dict)
        self._handle_dicts(ns_dict)
        return self._options_type(**ns_dict)

from inspect import signature
def get_argparser(func):
    sig = signature(func)
    if not sig.parameters:
        return ArgumentParser(None)
    first_param = next(iter(sig.parameters.values()), None)
    if is_dataclass(first_param.annotation):
        # def myfunc(all_of_my_args: MyArgType):
        return ArgumentParser(first_param.annotation)
    
    # If we make it down to here, it's epxected that we've wrapped a function like this:
    # def myfunc(arg1, arg2='hi',  arg3=True, arg4=4):
    # Let's try to translate this to a dataclass and re-use our prior code for argparsing dataclasses.
    dataclass = _sig_to_params_dataclass(func.__name__, sig)
    return ArgumentParser(dataclass, expand_dataclass_arg=True)

def func_to_params_dataclass(func):
    sig = signature(func)
    return _sig_to_params_dataclass(func.__name__, sig)

import dataclasses
def _sig_to_params_dataclass(func_name, sig):
    def _get_default_factory(p):
        # Workaround for what might be Python's most annoying gotcha.
        return lambda: p.default
    dc_params = []
    for param in sig.parameters.values():
        if param.annotation is sig.empty:
            raise TypeError(f"Will not guess parameter types, please annotate type for param {param.name!r}.")
        if param.default is not sig.empty:
            # I don't think there is any downside to always using default_factory rather than trying to use default,
            # and only using default_factory in the cases where dataclasses would throw a ValueError.
            dc_params.append((param.name, param.annotation, dataclasses.field(default_factory=_get_default_factory(param))))
        else:
            dc_params.append((param.name, param.annotation))

    returning = dataclasses.make_dataclass(f'{func_name.capitalize()}Args', dc_params)
    logger.debug(f"Made dataclass: {func_name}: {dc_params}")
    return returning

class CliApp:
    def __init__(self, main_cmd: Callable):
        """TODO Support for more than one cmd,  i.e. subcommands."""
        self._main_cmd = main_cmd

    def run(self, argv: Optional[List[str]]=None):
        parser = get_argparser(self._main_cmd)
        argobj = parser.parse_args(args=argv)
        if not parser.expand_dataclass_arg:
            self._main_cmd(argobj)
        else:
            logger.debug(f"argobj: {argobj}")
            self._main_cmd(**dataclasses.asdict(argobj))

    


from dataclasses import Field
class cli_field(Field):
    def __init__(
        self,
        *,
        # Missing defaults are when ArgumentParser can make smarter automatic decisions.
        cmdline: bool=MISSING,
        positional: bool=MISSING,
        short_flag: bool=MISSING,
        args: List[str]=MISSING,
        help: str=MISSING,
        choices: List=MISSING,

        # Copy-pasted super kwargs just for IDE autocomplete sake.
        default=MISSING, default_factory=MISSING, init=True, repr=True,
          hash=None, compare=True, metadata=None,

        **kwargs):

        if default is not MISSING and default_factory is not MISSING:
            raise ValueError('cannot specify both default and default_factory')

        metadata = kwargs.setdefault('metadata', {})
        for option in 'cmdline positional short_flag args help choices'.split():
            passed_val = eval(option)
            if passed_val is not MISSING:
                if option in metadata:
                    raise ValueError(f"Can't specify {option} as both argument to cli_field and metadata key.")
                metadata[option] = passed_val
        copy_pasted_kwargs = 'default default_factory init repr hash compare metadata'.split()
        exec("; ".join(f"kwargs['{kwarg}'] = {kwarg}" for kwarg in copy_pasted_kwargs))
        # kwargs.update({vars()[k] for k in copy_pasted_kwargs})
        super().__init__(**kwargs)


# New plan;
# Copy in invoke's parser and quit using argparse. Before we do that, should probably push so that can begin using.