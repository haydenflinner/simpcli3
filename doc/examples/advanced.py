from dataclasses import dataclass, field, MISSING
from enum import Enum
from typing import List

# from simpcli import task 
import sys
sys.path.append(r"D:\code\simpcli")

class PrintFormat(Enum):
    LINE_PER_ENTRY = 1
    PRETTY = 2

@dataclass
class ListDirectoryArgs:
    paths: List[str] = field(metadata=dict(positional=True))
    # Official python documentation says you can do "list[str]" but that is a lie.
    exclude: List[str] = field(default_factory=list)
    print_format: PrintFormat = PrintFormat.PRETTY
    follow_symlinks: bool = True

    # FAQ:
    # These aren't allowed, @dataclass doesn't pick them up as members.
    # One could write a custom @dataclass which does detect these and decide on a type for them, though.
    unannotated_value = ''
    unannotated_int = 4

def myls(lsargs: ListDirectoryArgs):
    print(f"Received args: {lsargs}\n")
    for path in lsargs.paths:
        print(path)

def mylazyfunc(paths: List[str], exclude: List[str] = [], follow_symlinks: bool=True):
    print(locals())
    print("hi")

def torture(listbools: List[bool] = [], pf_list: List[PrintFormat] = [PrintFormat.PRETTY]):
    print(locals())
    print("Done!")
# TODO document what is used from metadata: help, args, positional.
# TODO Releaseable / automated testing on real repo
# Simple API kind of like magicinvoke. Assume repeated if ends in s. Inspect defaults for type.

if __name__ == "__main__":
    from simpcli import argparse_dataclass
    import dataclasses
    parser = argparse_dataclass._get_argparser(myls)
    res = parser.parse_args()
    myls(res)

    import dataclasses
    res = argparse_dataclass._get_argparser(mylazyfunc).parse_args()
    mylazyfunc(**dataclasses.asdict(res))

    #
    # res = argparse_dataclass._get_argparser(torture).parse_args()
    # torture(**dataclasses.asdict(res))

