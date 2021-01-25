from dataclasses import dataclass, field, MISSING
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