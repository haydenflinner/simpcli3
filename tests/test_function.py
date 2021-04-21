"""Test simpcli3 functions."""

from io import StringIO
from textwrap import dedent

from simpcli3.cli import get_argparser, cli_field

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
    got = got.replace('__main__.py', 'pytest')
    print(got)
    print(expected)
    assert got == expected

from enum import Enum
from typing import List, Dict
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
usage: pytest [-h] --path str [--exclude str] [--no-follow-symlinks]
              [--print-format {LINE_PER_ENTRY,PRETTY}]

optional arguments:
  -h, --help            show this help message and exit
  --path str
  --exclude str
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
        force: bool = field(default=False, metadata=dict(short_flag=True))
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

    check_help(parser, """usage: pytest [-h] --myarg str

optional arguments:
  -h, --help   show this help message and exit
  --myarg str
""")

def test_cli_field_decorator():
    @dataclass
    class DataClass:
        my_special: int = cli_field(positional=True, help='myhelp')
    class MyClass:
        @classmethod
        def clsmethod(cls, myargs: DataClass):
            pass

    parser = helper(MyClass.clsmethod, '2'.split(), {'my_special': 2})

def test_cli_repeated_int():
    @dataclass
    class DataClass:
        my_special: List[int] = cli_field(positional=True, help='myhelp')
    class MyClass:
        @classmethod
        def clsmethod(cls, myargs: DataClass):
            pass

    parser = helper(MyClass.clsmethod, '2 4 6 8'.split(), {'my_special': [2, 4, 6, 8]})

def test_cli_short_flag():
    @dataclass
    class DataClass:
        my_special: List[int] = cli_field(short_flag='-i', help='myhelp')
    def f(myargs: DataClass):
        pass

    parser = helper(f, '-i 2 -i 4 --my-special 6 -i 8'.split(), {'my_special': [2, 4, 6, 8]})

def test_dict():
    # This feature is pretty half-baked but does at least work. Would like to verify that it interacts well with
    # short flags, so can pass "-Dx=y". If you don't like using =, can parse kwargs yourself for now.
    def f(config: Dict[str, int]):
        pass
    parser = helper(f, '--config x=2 --config y=5'.split(), {'config': {'x': 2, 'y': 5}})


def test_inheritance():
    @dataclass
    class Parent:
        my_int: int
    @dataclass
    class Child(Parent):
        my_float: float

    # TODO handle conflict
    def f(c: Child):
        pass

    parser = helper(f, '--my-int 1 --my-float 2.4'.split(), {'my_int': 1, 'my_float': 2.4})

"""TODO Doesn't currently work.
def test_composition():
    @dataclass
    class Box:
        my_int: int
    
    @dataclass
    class Item:
        my_box: Box
        my_float: float

    def f(c: Item):
        pass

    parser = helper(f, '--my-int 1 --my-float 2.4'.split(), {'my_int': 1, 'my_float': 2.4})
"""


"""
def test_nested_dataclasses():
    @dataclass
    class CommonArgs:
        verbose: bool = False
        version: bool = False
    @dataclass
    class DataClass:
        my_special: int = cli_field(choices=[1, 2, 3])
        ca: CommonArgs
        version: bool = True


    def f(myargs: DataClass):
        pass

    parser = helper(f, '--verbose --version --my-special 3'.split(), {'my_special': 3, 'ca': {'verbose': True, 'version': False}, 'version': False})
"""

def git_stash():
    """This will never work as long as we use default argparse; python argparser subcmd thing is too trash.
    """
    from typing import Optional

    @dataclass
    class GlobalGitConfig:
        email : str

    """
    class GitStash(CmdLineMixin, ConfigurableMixin):
        config : GlobalGitConfig

        def push(self, name: Optional[str]=None):
            name = name or "default-name"
            print(f"User {self.config.email} is pushing to stash with name: {name}")

        def pop(self, name: Optional[str]):
            name = name or "default-name"
            print(f"User {self.config.email} is popping to stash with name: {name}")

        cmd_line_default = pop

        # # Provided by default with Configurable mixin.
        # @classmethod
        # def from_config(cls, config: Config):
        #     instance = cls()
        #     instance.config = config
        #     return instance
    """

    from simpcli3.cli import get_argparser, cli_field, DefaultSubcommandArgParse
    def do_push():
        print("push")
    def do_pop():
        print("pop")

    # God this sucks
    a = DefaultSubcommandArgParse()
    b = a.add_subparsers()
    push = b.add_parser('push')
    push.set_defaults(func=do_push)
    push.add_argument('myarg1')

    pop = b.add_parser('pop')
    pop.set_defaults(func=do_pop)
    pop.add_argument('--myarg2')

    a.set_default_subparser('push')
    parsed_args = a.parse_args(['pop --help'])


    print(parsed_args)

    # if hasattr(parsed_args, 'func'):
        # parsed_args.func()
