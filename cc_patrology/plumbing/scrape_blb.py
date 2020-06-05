
import json
import re
import os
from bs4 import BeautifulSoup
import requests

from .utils import encode_ref


SUFFIX = r"^(?P<chapter>[0-9]+):(?P<verse>[0-9]+)(?P<extra>-[0-9]+)?$"
root = 'https://www.blueletterbible.org/'


def load_mapping(path='blb.mapping'):
    mapping = {}
    with open(path) as f:
        for line in f:
            blb_tag, bib_tag = line.strip().split('\t')
            mapping[blb_tag] = bib_tag

    return mapping


def parse_tag(tag, mapping):
    output, is_range = [], False

    start, *rest = tag
    book, start = start.split()
    m = re.search(SUFFIX, start)
    if not m:
        raise ValueError("skipping", start)

    book = mapping[book]
    groups = m.groupdict()
    chapter = int(groups['chapter'])
    verse = int(groups['verse'])
    output.append((book, str(chapter), str(verse)))

    extra = groups['extra']
    if extra:
        # drop leading hyphen
        extra = int(extra[1:])
        for i in range(verse + 1, extra):
            output.append((book, str(chapter), str(i)))
        is_range = True

    if rest:
        if len(output) > 1:
            raise ValueError("Got trailing ref for range ref", tag)

        is_range = True
        for idx, subtag in enumerate(rest, start=1):
            if not re.search(r"^[0-9]+$", subtag):
                print("skipping nested", subtag)
                continue

            subtag = int(subtag)
            if idx + verse != subtag:
                is_range = False
            output.append((book, str(chapter), str(subtag)))

    return output, is_range


def get_rtype(rtype, rest):
    # this is always '* Mere Allusions'
    if '*' in rtype:
        rtype = 'allusion'
    if rest:
        # this is always a cross meaning the reference is doubtfull
        rtype = '?'
    # assume 'reference' by default ('as it is written, etc...')
    if not rtype:
        rtype = 'reference'
    return rtype


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='output/blb.refs.json')
    args = parser.parse_args()

    mapping = load_mapping()
    # collect pages
    res = requests.get(os.path.join(root, 'study/misc/quotes.cfm'))
    soup = BeautifulSoup(res.content)
    parts = []
    for li in soup.find_all('li'):
        for a in li.find_all('a'):
            if a.attrs.get('href', '').startswith('/study/misc/quotes'):
                parts.append(a['href'][1:])  # drop leading "/"

    # collects pairs
    maps = []
    group = 0
    for a in parts:
        res = requests.get(os.path.join(root, a))
        soup = BeautifulSoup(res.content)
        div = soup.find("div", {'id': 'study'})

        for tr in div.find_all("tr", {"class": "label--cols"}):
            source, target, rtype, rest = tr.find_all("td")
            source = [a.text.strip() for a in source.find_all("a")]
            target = [a.text.strip() for a in target.find_all("a")]
            rtype = get_rtype(rtype.attrs.get('data-label', '').strip(),
                              rest.text.strip())
            try:
                source, is_range_s = parse_tag(source, mapping)
                target, is_range_t = parse_tag(target, mapping)
            except ValueError as e:
                print(e)
                continue
            if is_range_s and is_range_t:
                if not len(source) == len(target):
                    print("skipping unequal ranges with lengths",
                          len(source), len(target))
                    continue
                else:
                    for s_ref, t_ref in zip(source, target):
                        s_ref, t_ref = encode_ref(s_ref), encode_ref(t_ref)
                        maps.append({'source': s_ref, 'target': t_ref,
                                     'ref_type': rtype, 'group': group})
            elif (is_range_s and len(target) > 1) or (is_range_t and len(source) > 1):
                print("unequal lengths", len(source), len(target))
                print(source)
                print(target)
            else:
                for s_ref in source:
                    for t_ref in target:
                        maps.append({'source': encode_ref(s_ref),
                                     'target': encode_ref(t_ref),
                                     'ref_type': rtype, 'group': group})

            group += 1

    with open(args.target, 'w') as f:
        json.dump(maps, f)
