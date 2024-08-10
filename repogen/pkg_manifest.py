import json
import os
import urllib.parse
from datetime import datetime
from email.utils import parsedate_to_datetime
from json import JSONDecodeError
from typing import TypedDict, NotRequired, Literal
from urllib.parse import urljoin
from urllib.request import url2pathname

import requests

from repogen import cache
from repogen.common import url_fixup, url_size


class PackageHash(TypedDict):
    sha256: str


class PackageManifest(TypedDict):
    id: str
    title: str
    version: str
    type: str
    appDescription: str | None
    iconUri: str
    sourceUrl: NotRequired[str]
    rootRequired: NotRequired[bool | Literal['optional']]
    ipkUrl: str
    ipkHash: PackageHash
    ipkSize: NotRequired[int]
    installedSize: NotRequired[int]


def obtain_manifest(pkgid: str, channel: str, uri: str, offline: bool = False) -> tuple[PackageManifest, datetime]:
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme == 'file':
        manifest_path = url2pathname(parsed.path)
        try:
            with open(manifest_path, encoding='utf-8') as f:
                return json.load(f), datetime.fromtimestamp(os.stat(manifest_path).st_mtime)
        except (IOError, json.decoder.JSONDecodeError) as e:
            # XXX: not sure this should be happening; it was broken before
            #os.unlink(manifest_path)
            raise e
    else:
        cache_name = f'manifest_{pkgid}_{channel}.json'
        cache_file = cache.path(cache_name)
        try:
            if offline:
                raise requests.exceptions.ConnectionError('Offline')
            uri = url_fixup(uri)
            resp = requests.get(url=uri, allow_redirects=True)
            if resp.status_code != 200:
                raise requests.exceptions.HTTPError(f'Failed to fetch manifest: HTTP {resp.status_code}')
            manifest = resp.json()
            manifest['ipkUrl'] = urljoin(uri, manifest['ipkUrl'])
            manifest['ipkSize'] = url_size(manifest['ipkUrl'])
            with cache.open_file(cache_name, mode='w', encoding='utf-8') as f:
                json.dump(manifest, f)
            last_modified = datetime.now()
            if 'last-modified' in resp.headers:
                last_modified = parsedate_to_datetime(
                    resp.headers['last-modified'])
                os.utime(cache_file, (last_modified.timestamp(), last_modified.timestamp()))
            return manifest, last_modified
        except (requests.exceptions.JSONDecodeError, requests.exceptions.MissingSchema, requests.exceptions.InvalidSchema) as e:
            # XXX: fall back to cache?
            raise e
        except requests.exceptions.RequestException as e:
            if cache_file.exists():
                try:
                    with cache.open_file(cache_name, encoding='utf-8') as f:
                        return json.load(f), datetime.fromtimestamp(cache_file.stat().st_mtime)
                except (IOError, json.decoder.JSONDecodeError):
                    cache_file.unlink()
            raise e
