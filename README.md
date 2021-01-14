# simpcli3

TODO List
  1. Decorator for functions
  2. Decide on cmd / subcmd structure. Classes?
  3. In doc, recreate a few classic cmds
  4. args / kwargs support
  5. Mapping[str->something] support for e.g. cmake -Dx.y.z=21
  6. Tests for nested dataclass translation.
  7. Code to load JSON / YAML / Python configs, this goes with 8:
  8. SimpleCli and BigCli:
    a. SimpleCli accepts a function and returns something you an call .run() on to run the thing
    b. BigCli looks like the below:
  4. TODO parse richer types like dictionary? Like Dict as annotation type, so allow optional -Dmykey=myval
  5. TODO Support for loading Python, JSON / (optional YAML) configs




## TODO BigCli
```
class MyApp:
    def __init__(self, config):
        self._config = config

    def ln(self, in:str,  out:str):
        pass
    
    def cp(self, in:str, out:str):
        pass

run(MyApp)

--help:
myapp {ln, cp}
myapp ln --help
   prints that help.

TODO Check invoke here because they have better subcmd help than argparse.
```


### Improvements over projects based on
Modifications made from "argparse_dataclass":
  2. "positional" metadata arg as I think that's more intuitive than passing "args" directly.
  3. If type is enum, choices automatically specified, default given as string
     (kind of like "argparse_dataclasses" package, but with cleaner impl IMO)
  4. Better handling of bools (especially ones which default to True).
  5. Wrapper over field (idea lifted from argparse_dataclasses)