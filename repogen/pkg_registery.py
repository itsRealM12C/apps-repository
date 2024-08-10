import importlib
from pathlib import Path
from typing import TypedDict, NotRequired, Literal, List

import yaml


class PackageRequirements(TypedDict):
    webosRelease: NotRequired[str]
    deviceSoC: NotRequired[List[str]]


class PackageRegistry(TypedDict):
    title: str
    iconUri: str
    manifestUrl: str
    manifestUrlBeta: NotRequired[str]
    category: str
    description: str
    pool: Literal['main', 'non-free']
    requirements: NotRequired[PackageRequirements]
    detailIconUri: NotRequired[str]
    funding: NotRequired[dict[str, List[str]]]


def parse_yml_package(p: Path) -> tuple[str, PackageRegistry]:
    with p.open(encoding='utf-8') as f:
        content: PackageRegistry = yaml.safe_load(f)
    return p.stem, content


# noinspection PyUnresolvedReferences
def load_py_package(p: Path) -> tuple[str, PackageRegistry]:
    pkgid = p.stem
    spec = importlib.util.spec_from_file_location(f"pkg.{pkgid}", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return pkgid, module.load()
