import locale
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict, List, NotRequired

import nh3

from repogen import validators
from repogen.common import url_fixup
from repogen.pkg_manifest import obtain_manifest, PackageManifest
from repogen.pkg_registery import PackageRequirements, PackageRegistry, parse_yml_package, load_py_package

locale.setlocale(locale.LC_TIME, '')


class PackageInfo(TypedDict):
    id: str
    title: str
    iconUri: str
    manifestUrl: str
    manifestUrlBeta: NotRequired[str]
    category: str
    description: str
    detailIconUri: NotRequired[str]
    funding: NotRequired[dict]
    pool: str
    requirements: NotRequired[PackageRequirements]
    manifest: PackageManifest
    manifestBeta: NotRequired[PackageManifest]
    lastmodified: datetime
    lastmodified_str: str


def load_registry(info_path: Path) -> tuple[str, PackageRegistry]:
    extension = info_path.suffix
    content: PackageRegistry
    if extension == '.yml':
        pkgid, content = parse_yml_package(info_path)
    elif extension == '.py':
        pkgid, content = load_py_package(info_path)
    else:
        raise ValueError(f'Unrecognized info format {extension}')
    validator = validators.for_schema('packages/PackageInfo.json')
    validator.validate(content)
    return pkgid, content


def from_package_info_file(info_path: Path, offline=False) -> PackageInfo:
    pkgid, content = load_registry(info_path)
    return from_package_info(pkgid, content, offline)


def from_package_info(pkgid: str, content: PackageRegistry, offline=False) -> PackageInfo:
    print(f'Parsing package info for {pkgid}', file=sys.stderr)
    manifest_url = url_fixup(content['manifestUrl'])
    pkginfo: PackageInfo = {
        'id': pkgid,
        'title': content['title'],
        'iconUri': content['iconUri'],
        'manifestUrl': manifest_url,
        'category': content['category'],
        'description': nh3.clean(content.get('description', ''), attributes={
            'a': {'href', 'hreflang'},
            'bdo': {'dir'},
            'blockquote': {'cite'},
            'col': {'align', 'char', 'charoff', 'span'},
            'colgroup': {'align', 'char', 'charoff', 'span'},
            'del': {'cite', 'datetime'},
            'h1': {'align'},
            'hr': {'align', 'size', 'width'},
            'img': {'align', 'alt', 'height', 'src', 'width'},
            'ins': {'cite', 'datetime'},
            'ol': {'start'},
            'p': {'align'},
            'q': {'cite'},
            'table': {'align', 'char', 'charoff', 'summary'},
            'tbody': {'align', 'char', 'charoff'},
            'td': {'align', 'char', 'charoff', 'colspan', 'headers', 'rowspan'},
            'tfoot': {'align', 'char', 'charoff'},
            'th': {'align', 'char', 'charoff', 'colspan', 'headers', 'rowspan', 'scope'},
            'thead': {'align', 'char', 'charoff'},
            'tr': {'align', 'char', 'charoff'}
        }, link_rel=None),
    }
    if 'detailIconUri' in content:
        pkginfo['detailIconUri'] = content['detailIconUri']
    if 'funding' in content:
        pkginfo['funding'] = content['funding']
    pkginfo['pool'] = valid_pool(content['pool'])
    if 'requirements' in content:
        pkginfo['requirements'] = content['requirements']
    manifest, lastmodified_r = obtain_manifest(pkgid, 'release', manifest_url, offline)
    if manifest:
        pkginfo['manifest'] = manifest
    lastmodified_b = None
    if 'manifestUrlBeta' in content:
        manifest_b, lastmodified_b = obtain_manifest(pkgid, 'beta', url_fixup(content['manifestUrlBeta']))
        if manifest_b:
            pkginfo['manifestBeta'] = manifest_b
    lastmodified = lastmodified_r, lastmodified_b
    pkginfo['lastmodified'] = max(d for d in lastmodified if d is not None)
    pkginfo['lastmodified_str'] = pkginfo['lastmodified'].strftime('%Y/%m/%d %H:%M:%S %Z')
    return pkginfo


def list_packages(pkgdir: Path, packages: List[str] | None = None, offline: bool = False) -> List[PackageInfo]:
    paths: List[Path] = [f for f in pkgdir.iterdir() if f.is_file()]

    def map_package_info(p: Path) -> PackageInfo | None:
        pkgid, content = load_registry(p)
        if packages and pkgid not in packages:
            return None
        try:
            return from_package_info(pkgid, content, offline)
        except Exception as e:
            print(f'Error loading package info file {p.name}: {e}', file=sys.stderr)
            return None

    return sorted(filter(lambda x: x, map(map_package_info, paths)), key=lambda x: x['title'])


def valid_pool(value: str) -> str:
    if value not in ['main', 'non-free']:
        raise ValueError(f'Unknown pool type {value}')
    return value
