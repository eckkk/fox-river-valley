from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _module_name_from_path(path_text: str) -> str:
    path = Path(path_text)
    if path.suffix == ".py":
        path = path.with_suffix("")
    return ".".join(path.parts)


def _load_suite(args: list[str]) -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    targets = [arg for arg in args if not arg.startswith("-")]
    if not targets:
        return loader.discover("tests")

    suites: list[unittest.TestSuite] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            suites.append(loader.discover(str(path)))
        elif path.suffix == ".py":
            suites.append(loader.loadTestsFromName(_module_name_from_path(target)))
        else:
            suites.append(loader.loadTestsFromName(target))
    return unittest.TestSuite(suites)


def main() -> int:
    args = sys.argv[1:]
    quiet = "-q" in args or "--quiet" in args
    suite = _load_suite(args)
    result = unittest.TextTestRunner(verbosity=1 if quiet else 2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
