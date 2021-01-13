"""
``argparse_dataclass``
======================

Declarative CLIs with ``argparse`` and ``dataclasses``.

.. image:: https://travis-ci.org/mivade/argparse_dataclass.svg?branch=master
    :target: https://travis-ci.org/mivade/argparse_dataclass

.. image:: https://img.shields.io/pypi/v/argparse_dataclass
    :alt: PyPI

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

Examples
--------

A simple parser with flags:

.. code-block:: pycon

    >>> from dataclasses import dataclass
    >>> from argparse_dataclass import ArgumentParser
    >>> @dataclass
    ... class Options:
    ...     verbose: bool
    ...     other_flag: bool
    ...
    >>> parser = ArgumentParser(Options)
    >>> print(parser.parse_args([]))
    Options(verbose=False, other_flag=False)
    >>> print(parser.parse_args(["--verbose", "--other-flag"]))
    Options(verbose=True, other_flag=True)

Using defaults:

.. code-block:: pycon

    >>> from dataclasses import dataclass, field
    >>> from argparse_dataclass import ArgumentParser
    >>> @dataclass
    ... class Options:
    ...     x: int = 1
    ...     y: int = field(default=2)
    ...     z: float = field(default_factory=lambda: 3.14)
    ...
    >>> parser = ArgumentParser(Options)
    >>> print(parser.parse_args([]))
    Options(x=1, y=2, z=3.14)

Enabling choices for an option:

.. code-block:: pycon

    >>> from dataclasses import dataclass, field
    >>> from argparse_dataclass import ArgumentParser
    >>> @dataclass
    ... class Options:
    ...     small_integer: int = field(metadata=dict(choices=[1, 2, 3]))
    ...
    >>> parser = ArgumentParser(Options)
    >>> print(parser.parse_args(["--small-integer", "3"]))
    Options(small_integer=3)

Using different flag names and positional arguments:

.. code-block:: pycon

    >>> from dataclasses import dataclass, field
    >>> from argparse_dataclass import ArgumentParser
    >>> @dataclass
    ... class Options:
    ...     x: int = field(metadata=dict(args=["-x", "--long-name"]))
    ...     positional: str = field(metadata=dict(args=["positional"]))
    ...
    >>> parser = ArgumentParser(Options)
    >>> print(parser.parse_args(["-x", "0", "positional"]))
    Options(x=0, positional='positional')
    >>> print(parser.parse_args(["--long-name", 0, "positional"]))
    Options(x=0, positional='positional')

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

"""
Modifications made from original:
  2. "positional" metadata arg as I think that's more intuitive than passing "args" directly.
  3. If type is enum, choices automatically specified, default given as string.
  4. Better handling of bools (especially ones which default to True).
  4. TODO parse richer types like dictionary? Like Dict as annotation type, so allow optional -Dmykey=myval
  5. TODO Support for loading Python, JSON / (optional YAML) configs


"""
import argparse
from contextlib import suppress
from dataclasses import is_dataclass, MISSING, fields
from enum import Enum
from typing import TypeVar

__version__ = "0.1.0"

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
        self._posarg_stored_as = {}
        self._auto_deplural = auto_deplural
        self.expand_dataclass_arg = expand_dataclass_arg


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
    
    def _determine_flagname(self, param_name, repeated):
        if repeated and len(param_name) > 3 and param_name.endswith('s'):
            param_name = param_name[:-1]  # remove last s, that is e.g. GccArgs.excludes becomes --exclude
        return f"{param_name.strip('_').replace('_', '-')}"

    def _determine_flags(self, param_name, repeated, positional, allow_short_flag):
        flagname = self._determine_flagname(param_name, repeated)
        if not positional:
            returning = []
            if allow_short_flag:
                returning.append(f'-{param_name[0]}')
            returning.append(f"--{flagname}")
            return returning
        else:
            return [f'{flagname}']

    def _disable_flags(self, param_name, repeated):
        flagname = self._determine_flagname(param_name, repeated)
        return [f"--no-{flagname}"]

    def _elem_type(self, thetype):
        # TODO Test coverage of this.
        try:
            elem_type = thetype.__args__[0]
            # TODO fix to logging.debug
            # print(f"Determined {thetype} had elements of type: {elem_type}")
            return elem_type, True
        except Exception:
            return thetype, False

    def _get_enum_parser(self, enum_type):
        def parse_enum(val):
            # I have no idea why they chose this syntax for parsing a string.
            return enum_type[val]
        return parse_enum

    def _add_dataclass_options(self, options_type) -> None:
        if not is_dataclass(options_type):
            raise TypeError(f"cls must be a dataclass, but given {self._options_type}")

        for field in fields(options_type):
            if not field.metadata.get("cmdline", True):
                continue
            elem_type, repeated = self._elem_type(field.type)
            positional = (('args' in field.metadata and not field.metadata['args'][0].startswith('-'))
                or bool(field.metadata.get('positional')))
            allow_short_flag = field.metadata.get('allow_short_flag')
            if positional and allow_short_flag:
                raise ValueError("Can't have a positional argument with a flag.")
            args = field.metadata.get("args", self._determine_flags(field.name, repeated, positional, allow_short_flag))
            if positional:
                self._posarg_stored_as[args[0]] = field.name

            if is_dataclass(elem_type):
                # self._add_dataclass_options(elem_type)  # This would be interesting.
                # TODO Strategy:
                #   1. Recurse and include all of the flags
                #   2. Map those flags back to this instance of this type.
                raise ValueError("TODO, Currently do not support dataclass members.")
            kwargs = {
                "type": elem_type,
                "help": field.metadata.get("help", None),
            }

            # We want to ensure that we store the argument based on the
            # name of the field and not whatever flag name was provided
            if not positional:
                # For some reason argparse doesn't like a different dest for a positional arg.
                kwargs["dest"] = field.name

            if field.metadata.get("choices") is not None:
                kwargs["choices"] = field.metadata["choices"]
            elif issubclass(elem_type, Enum):
                # kwargs["choices"] = [elem.name for elem in elem_type]
                kwargs["choices"] = [elem for elem in elem_type]

            if field.default == field.default_factory == MISSING and not positional:
                kwargs["required"] = True
            else:
                if field.default_factory is not MISSING:
                    kwargs["default"] = field.default_factory()
                    print(f"Set default for {field.name} to {kwargs['default']}")
                else:
                    # if field.default is MISSING:
                        # TODO Special MISSING whose __str__ isn't ugly?
                    #    field.default = 
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
                    args = field.metadata.get("args", self._disable_flags(field.name, repeated))
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

            print(f"add_argument: {args} {kwargs}")
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

    def parse_args(self, *args, **kwargs) -> OptionsType:
        """Parse arguments and return as the dataclass type."""
        namespace = super().parse_args(*args, **kwargs)
        ns_dict = vars(namespace)
        self._handle_empty_posarg(ns_dict)
        self._handle_missing(ns_dict)
        print(f"Expanding: {ns_dict}")
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
    return ArgumentParser(dataclass)

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
    print(f"Made dataclass: {func_name}: {dc_params}")
    return returning

class CliApp:
    def __init__(self, *, main_cmd: callable):
        """TODO Support for more than one cmd,  i.e. subcommands."""
        self._main_cmd = main_cmd

    def run(self, argv=None):
        parser = get_argparser(self._main_cmd)
        args = parser.parse_args()
        if not parser.expand_dataclass_arg:
            self._main_cmd(args)
        else:
            self._main_cmd(**args)

# TODO Add a decorator here using 'decorator' or 'wrapt' module.

def run(args):
    pass