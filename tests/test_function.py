"""Test simpcli3 functions."""

from simpcli3.cli import get_argparser

def get_wrapper(func, **kwargs):
    return get_argparser(func, **kwargs)

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
    parser = get_wrapper(ls1)
    data = parser.parse_args('--path x'.split())
    assert dataclasses.asdict(data) == dict(paths=['x'], excludes=[], follow_symlinks=True, print_format=PrintFormat.PRETTY)
    data = parser.parse_args('--path x --exclude y --no-follow-symlinks --print-format LINE_PER_ENTRY'.split())
    assert dataclasses.asdict(data) == dict(paths=['x'], excludes=['y'], follow_symlinks=False, print_format=PrintFormat.LINE_PER_ENTRY)

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

    parser = get_wrapper(ls2)
    data = parser.parse_args([])
    assert dataclasses.asdict(data) == dict(paths=[], excludes=[], follow_symlinks=True, print_format=PrintFormat.PRETTY)
    data = parser.parse_args('x1'.split())
    assert dataclasses.asdict(data) == dict(paths=['x1'], excludes=[], follow_symlinks=True, print_format=PrintFormat.PRETTY)
    data = parser.parse_args('x1 x2 x3 --exclude y --no-follow-symlinks --print-format LINE_PER_ENTRY'.split())
    assert dataclasses.asdict(data) == dict(paths=['x1', 'x2', 'x3'], excludes=['y'], follow_symlinks=False, print_format=PrintFormat.LINE_PER_ENTRY)

    data = parser.parse_args('x --exclude y'.split())
    assert dataclasses.asdict(data) == dict(paths=['x'], excludes=['y'], follow_symlinks=True, print_format=PrintFormat.PRETTY)

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
    parser = get_wrapper(ln)
    data = parser.parse_args('x1 x2'.split())
    assert dataclasses.asdict(data) == {'input': 'x1', 'output': 'x2', 'force': False}
    data = parser.parse_args('x1 x2 -f'.split())
    assert dataclasses.asdict(data) == {'input': 'x1', 'output': 'x2', 'force': True}

