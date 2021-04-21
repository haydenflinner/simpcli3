# simpcli3
A Python3 module for turning functions into cmd-line programs trivially.


## Examples
### Non-dataclass (simple function) example
```
from simpcli3 import CliApp
from typing import List

def myls(paths: List[str], exclude: List[str]=[], mystr: str=None, follow_symlinks: bool=False):
    print(f"Received args: {paths}\n")
    for path in paths:
        print(path)

if __name__ == "__main__":
    CliApp(myls).run()
```

### More advanced Example
This example actually uses a dataclass argument rather than a collection of arguments of primitive types.

```
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
```

## Looking Forward

It would be nice to also be able to parse JSON / TOML config files into dataclasses, rather than having ever-growing cmd-line args.

### Prior Art
And why I didn't use it.

For argparse_dataclasses and argparse_dataclass reasons, see Improvements.

SimpleParsing (pip install simple_parsing). Different goals and approaches in terms of simplicity. For one, we
don't depend on numpy.


#### Improvements over projects based on
Modifications made from "argparse_dataclass":
  2. "positional" metadata arg as I think that's more intuitive than passing "args" directly.
  3. If type is enum, choices automatically specified, default given as string
     (kind of like "argparse_dataclasses" package, but with cleaner impl IMO)
  4. Better handling of bools (especially ones which default to True).
  5. Wrapper over field (idea lifted from argparse_dataclasses)