# Python Afire [![PyPI](https://img.shields.io/pypi/pyversions/fire.svg?style=plastic)](https://github.com/google/python-fire)

Fork from [python-fire](https://github.com/google/python-fire). ***support type conversion based on the type hints.***

_Python AFire is a library for automatically generating command line interfaces
(CLIs) from absolutely any Python object._


-   Python Afire is a simple way to create a CLI in Python.
    [[1]](docs/benefits.md#simple-cli)
-   Python Afire is a helpful tool for developing and debugging Python code.
    [[2]](docs/benefits.md#debugging)
-   Python Afire helps with exploring existing code or turning other people's
    code into a CLI. [[3]](docs/benefits.md#exploring)
-   Python Afire makes transitioning between Bash and Python easier.
    [[4]](docs/benefits.md#bash)
-   Python Afire makes using a Python REPL easier by setting up the REPL with the
    modules and variables you'll need already imported and created.
    [[5]](docs/benefits.md#repl)
-   Python Afire **fully support type hint.**

## Installation

To install Python Afire with pip, run: `pip install afire`

To install Python Afire with conda, run: `conda install afire -c conda-forge`

To install Python Afire from source, first clone the repository and then run:
`poetry install`

## Basic Usage

You can call `Fire` on any Python object:<br>
functions, classes, modules, objects, dictionaries, lists, tuples, etc.
They all work!

Here's an example of calling Fire on a function with type hint, it will automatically recognize and convert types according to your type hint.

```python
import afire
from pathlib import Path

def hello(path: Path):
  assert isinstance(path, Path)

if __name__ == '__main__':
  afire.Fire(hello)
```

Then, from the command line, you can run:

```bash
python hello.py --path=/root  # No error
python hello.py --help  # Shows usage information.
```

Here's an example of calling Fire on a function with nested type hint.

```python
import afire
from typing import Dict, Union, Set

def test(a: Union[Dict[str, int], Set[bytes]]):
  # check types
  assert isinstance(a, (Dict, Set))

  # check types in dict or set
  if isinstance(a, Dict):
    for k, v in a.items():
      assert isinstance(k, str)
      assert isinstance(v, int)
  else:
    for i in a:
      assert isinstance(i, bytes)
  print(a)

if __name__ == '__main__':
  afire.Fire(test)
```

Then, from the command line, you can run:

```bash
# dict type
python test.py --a='{1: 2}'  # {'1': 2}
# or use position arg
python test.py '{1: 2}'  # {'1': 2}

# set type
python test.py --a='{a, b, c}'  # {b'a', b'b', b'c'}
```
## Type conversion rules

Currently support input types:
| type  | example     |
| :---- | :---------- |
| str   | `"a"`       |
| int   | `1`         |
| bytes | `b"a"`      |
| List  | `[x, y, z]` |
| Dict  | `{x: y}`    |
| Set   | `{x, y, z}` |
| Tuple | `(x, y, z)` |

***note: you can use str or bytes expr in complex type, e.g. [b"x", b"y"]***
### Rule

|                             |             str             |          int           |   bytes    | **<- input** |
| :-------------------------: | :-------------------------: | :--------------------: | :--------: | :----------: |
|             str             |              *              |           *            |     *      |              |
|             int             |   can be converted to int   |           *            |     x      |              |
|            bytes            |           *(utf8)           | *(length 8, big order) |     *      |              |
|        datetime/date        | format: YYYY-MM-DD-HH:MM:SS |           x            |     x      |              |
|                             | format: YYYY-MM-DD HH:MM:SS |                        |            |              |
|                             | format: YYYY/MM/DD HH:MM:SS |                        |            |              |
|                             |   format: YYYYMMDDHHMMSS    |                        |            |              |
|                             |     format: YYYY/MM/DD      |                        |            |              |
|                             |     format: YYYY-MM-DD      |                        |            |              |
| any type with one parameter |         if support          |       if support       | if support |              |
|      e.g. Path, float       |                             |                        |            |
|       **^ type hint**       |                             |                        |            |              |

*: any kind of input will convert

x: not support to convert

***Currently relation type hint only support `Union` and `Optional`.***
## License

Licensed under the
[Apache 2.0](https://github.com/google/python-fire/blob/master/LICENSE) License.

## Disclaimer

This is not an official Google product.
