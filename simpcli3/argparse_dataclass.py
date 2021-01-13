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

    def __init__(self, options_class: OptionsType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options_type: OptionsType = options_class
        self._posarg_name = None
        if self._options_type:
            self._add_dataclass_options(self._options_type)

    def _determine_flags(self, param_name):
        return [f"--{param_name.strip('_').replace('_', '-')}"]

    def _disable_flags(self, param_name):
        return [f"--no-{param_name.strip('_').replace('_', '-')}"]

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
            args = field.metadata.get("args", self._determine_flags(field.name))
            positional = (not args[0].startswith("-")) or bool(field.metadata.get('positional'))
            if positional:
                if self._posarg_name:
                    raise TypeError("Can't have multiple positional args, but saw at least {} and {}".format(
                        self._posarg_name, positional
                    ))
                self._posarg_name = field.name

            elem_type, repeated = self._elem_type(field.type)
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
            kwargs["dest"] = field.name

            if field.metadata.get("choices") is not None:
                kwargs["choices"] = field.metadata["choices"]
            elif issubclass(elem_type, Enum):
                # kwargs["choices"] = [elem.name for elem in elem_type]
                kwargs["choices"] = [elem for elem in elem_type]

            if field.default == field.default_factory == MISSING and not positional:
                kwargs["required"] = True
            else:
                if field.default_factory != MISSING:
                    kwargs["default"] = field.default_factory()
                else:
                    kwargs["default"] = field.default
                # if isinstance(kwargs["default"], Enum):
                #   kwargs["default"] = kwargs["default"].name
                    # TODO default here need to change if repeated?

            if field.type is bool:
                if field.default:
                    kwargs["action"] = "store_false"
                    args = field.metadata.get("args", self._disable_flags(field.name))
                else:
                    kwargs["action"] = "store_true"
                
                for key in ("type", "required"):
                    with suppress(KeyError):
                        kwargs.pop(key)
            if repeated:
                kwargs["action"] = "append"
                if kwargs.get("default") is MISSING:
                    print("HERRO")
                    kwargs["default"] = []

            if issubclass(elem_type, Enum):
                kwargs["type"] = self._get_enum_parser(elem_type)

            print(f"add_argument: {args} {kwargs}")
            self.add_argument(*args, **kwargs)

    def _handle_empty_posarg(self, ns_dict):
        if not self._posarg_name:
            return
        # Can't create a dataclass without providing a all args unless they have defaults.
        # In the case of a positional arg without default, we will have arg_name=MISSING here,
        # rather than the arg not being provided, which dataclass accepts as the value without question.
        # bool(MISSING()) == True, so can't expect user to guard against with "if not myargs.posarg".
        # It is tempting to raise an argparsing error here. But the ideal solution seems to be to pass [].
        # This way, if the user prefers that an empty list isn't a valid argument, they can raise the TypeError themselves,
        # And this also prevents other Python functions calling into it with an empty list.
        if self._posarg_name in ns_dict and ns_dict[self._posarg_name] is MISSING:
            ns_dict[self._posarg_name] = []


    def parse_args(self, *args, **kwargs) -> OptionsType:
        """Parse arguments and return as the dataclass type."""
        namespace = super().parse_args(*args, **kwargs)
        ns_dict = vars(namespace)
        self._handle_empty_posarg(ns_dict)
        return self._options_type(**ns_dict)

from inspect import signature
def _get_argparser(func):
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

import dataclasses
def _sig_to_params_dataclass(func_name, sig):
    dc_params = []
    for param in sig.parameters.values():
        if param.annotation is sig.empty:
            raise TypeError(f"Will not guess parameter types, please annotate type for param {param.name!r}.")
        if param.default is not sig.empty:
            # I don't think there is any downside to always using default_factory rather than trying to use default,
            # and only using default_factory in the cases where dataclasses would throw a ValueError.
            dc_params.append((param.name, param.annotation, dataclasses.field(default_factory=lambda: param.default)))
        else:
            dc_params.append((param.name, param.annotation))

    returning = dataclasses.make_dataclass(f'{func_name.capitalize()}Args', dc_params)
    return returning