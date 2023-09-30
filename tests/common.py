from afire import Fire
from pathlib import Path
from datetime import datetime
from typing import Dict


if __name__ == "__main__":

    def test(d: Dict[int, Dict[str, datetime]], path: Path):
        print(repr(d))
        print(path, type(path))

    Fire(test, ["--d", '{1: {2: "2023-09-10"}}', "--path", "/xxx/yyyy"])
