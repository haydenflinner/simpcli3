"""Test simpcli3 functions."""

from io import StringIO
from textwrap import dedent

from simpcli3.cli import get_argparser

def get_wrapper(func, **kwargs):
    return get_argparser(func, **kwargs)

def helper(func_or_parser, arglist, expect):
    if callable(func_or_parser):
        parser = get_wrapper(func_or_parser)
    else:
        parser = func_or_parser
    data = parser.parse_args(arglist)
    assert dataclasses.asdict(data) == expect
    return parser

def check_help(parser, expected):
    out = StringIO()
    parser.print_help(out)
    # expected = dedent(expected)
    got = out.getvalue()
    print(got)
    print(expected)
    assert got == expected

from enum import Enum
from typing import List
from dataclasses import dataclass, field
import dataclasses

class PrintFormat(Enum):
    LINE_PER_ENTRY = 1
    PRETTY = 2

def test_low_effort_function():
    # TODO Decorator and test it here
    # data = {}
    def ls1(paths: List[str], excludes: List[str] = [], follow_symlinks: bool=True, print_format: PrintFormat = PrintFormat.PRETTY):
        # print(locals())
        # print("hi")
        # data.update(locals())
        pass
    parser = helper(ls1, '--path x'.split(), dict(paths=['x'], excludes=[], follow_symlinks=True, print_format=PrintFormat.PRETTY))
    helper(parser, '--path x --exclude y --no-follow-symlinks --print-format LINE_PER_ENTRY'.split(),
        dict(paths=['x'], excludes=['y'], follow_symlinks=False, print_format=PrintFormat.LINE_PER_ENTRY))
    check_help(parser, """
usage: pytest [-h] --path PATHS [--exclude EXCLUDES] [--no-follow-symlinks] [--print-format {LINE_PER_ENTRY,PRETTY}]

optional arguments:
  -h, --help            show this help message and exit
  --path PATHS
  --exclude EXCLUDES
  --no-follow-symlinks
  --print-format {LINE_PER_ENTRY,PRETTY}
""".lstrip())

def test_proper_function():
    # TODO Decorator and test it here
    @dataclass
    class LsArgs:
        paths: List[str] = field(metadata=dict(positional=True))
        excludes: List[str] = field(default_factory=lambda: [])
        follow_symlinks: bool = True
        print_format: PrintFormat = PrintFormat.PRETTY
    def ls2(ls_args: LsArgs):
        pass

    parser = helper(ls2, [], dict(paths=[], excludes=[], follow_symlinks=True, print_format=PrintFormat.PRETTY))
    helper(parser, 'x1'.split(),
      dict(paths=['x1'], excludes=[], follow_symlinks=True, print_format=PrintFormat.PRETTY))
    helper(parser, 'x1 x2 x3 --exclude y --no-follow-symlinks --print-format LINE_PER_ENTRY'.split(),
      dict(paths=['x1', 'x2', 'x3'], excludes=['y'], follow_symlinks=False, print_format=PrintFormat.LINE_PER_ENTRY))

    helper(parser, 'x --exclude y'.split(),
      dict(paths=['x'], excludes=['y'], follow_symlinks=True, print_format=PrintFormat.PRETTY))

def test_low_effort_function_2():
    @dataclass
    class LnArgs:
        input: str = field(metadata=dict(positional=True))
        output: str = field(metadata=dict(positional=True))
        force: bool = field(default=False, metadata=dict(allow_short_flag=True))
    # @datacmd(defaults=ln_args_instance)
    # def ln(ln_args: LnArgs = ln_args_instance):  # TODO Allow this, or this
    def ln(ln_args: LnArgs):
        pass
    parser = helper(ln, 'x1 x2'.split(), {'input': 'x1', 'output': 'x2', 'force': False})
    helper(parser, 'x1 x2 -f'.split(),  {'input': 'x1', 'output': 'x2', 'force': True})

def test_cls_static_method_1():
    class MyClass:
        @classmethod
        def clsmethod(cls, myargs: List[str]):
            pass
        @staticmethod
        def statmethod(myargs: List[str]):
            pass

    parser = helper(MyClass.clsmethod, '--myarg x1 --myarg x2'.split(), {'myargs': ['x1', 'x2']})
    helper(MyClass.statmethod, '--myarg x1 --myarg x2'.split(), {'myargs': ['x1', 'x2']})

    check_help(parser, """usage: pytest [-h] --myarg MYARGS

optional arguments:
  -h, --help      show this help message and exit
  --myarg MYARGS
""")


"""
# TODO This doesn't work. Probably just need to bypass argparse?
def test_args():
    @dataclass
    class Args:
        input: List[str] = field(metadata=dict(positional=True))
    def echo(myargs: Args):
        pass

   or
   def echo(*args):
       pass

    parser = get_wrapper(echo)
    passed = 'x1 x2 --flag1 --flag2 ok'.split()
    data = parser.parse_args(passed)
    assert data == {'input': passed}
"""

