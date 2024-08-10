# -*- coding: utf-8 -*-
import math
from pathlib import Path
from typing import List

import more_itertools
import pystache

from repogen import pkg_info
from repogen.common import ITEMS_PER_PAGE, ensure_open
from repogen.pkg_info import PackageInfo


class AppListingGenerator:

    def __init__(self, packages: List[PackageInfo]):
        with Path(__file__).parent.joinpath('templates', 'apps', 'detail.md').open(encoding='utf-8') as f:
            self.details_template = f.read()
        with Path(__file__).parent.joinpath('templates', 'apps', 'list.html').open(encoding='utf-8') as f:
            self.index_template = f.read()

        self.packages = packages

    def gen_details(self, outdir: Path):
        for pkg in self.packages:
            with ensure_open(outdir.joinpath('%s.md' % pkg['id']), mode='w', encoding='utf-8') as f:
                f.write(pystache.render(self.details_template, pkg))

    def _gen_page(self, outdir: Path, items, pagination):
        page = pagination['page']
        maxp = pagination['max']
        prevp = pagination['prev']
        nextp = pagination['next']

        def _nav_path(p: int):
            return 'apps' if p == 1 else 'apps/page/%d' % p

        prev_href = _nav_path(prevp) if prevp else None
        next_href = _nav_path(nextp) if nextp else None

        nav_center_start = page - 4
        nav_center_end = page + 4
        if nav_center_start < 1:
            nav_center_end = nav_center_end + 1 - nav_center_start
            nav_center_start = 1
        if nav_center_end > maxp:
            nav_center_end = maxp

        def _nav_item(p: int):
            return {'page': p, 'path': _nav_path(p), 'current': p == page}

        page_links = list(map(_nav_item, range(
            nav_center_start, nav_center_end + 1)))
        if page > 4:
            page_links = page_links[1:]
            page_links = [_nav_item(1), None] + page_links
        if page < maxp - 3:
            page_links = page_links[:-1]
            page_links = page_links + [None, _nav_item(maxp)]

        def _page_path(p: int):
            return 'apps/index.html' if p == 1 else 'apps/page/%d.html' % p

        with ensure_open(outdir.joinpath('apps-page-%d.html' % page), mode='w', encoding='utf-8') as f:
            f.write(pystache.render(self.index_template, {
                'packages': items, 'pagePath': _page_path(page),
                'firstPage': page == 1,
                'pagination': {
                    'page': page, 'maxPage': maxp, 'pageLinks': page_links,
                    'prevPath': prev_href, 'nextPath': next_href
                }
            }))

    def gen_list(self, outdir: Path):
        pkgs = self.packages
        packages_length = len(pkgs)
        max_page = math.ceil(packages_length / ITEMS_PER_PAGE)
        for index, items in enumerate(more_itertools.chunked(pkgs, ITEMS_PER_PAGE)):
            page = index + 1
            pagination = {
                'prev': page - 1 if page > 1 else None,
                'next': page + 1 if page < max_page else None,
                'page': page, 'max': max_page,
            }
            self._gen_page(outdir, items, pagination)


def generate(packages: List[PackageInfo], outdir: Path, gen_details=True, gen_list=True):
    generator = AppListingGenerator(packages)

    if gen_details:
        generator.gen_details(outdir)
    if gen_list:
        generator.gen_list(outdir)

    print('Generated application page for %d packages.' %
          len(generator.packages))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input-dir', required=True)
    parser.add_argument('-o', '--output-dir', required=True)
    args = parser.parse_args()

    generate(pkg_info.list_packages(Path(args.input_dir)), Path(args.output_dir))
