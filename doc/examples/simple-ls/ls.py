from simpcli3 import CliApp
from typing import List

def myls(paths: List[str], exclude: List[str]=[], mystr: str=None, follow_symlinks: bool=False):
    print(f"Received args: {paths}\n")
    for path in paths:
        print(path)

if __name__ == "__main__":
    CliApp(myls).run()