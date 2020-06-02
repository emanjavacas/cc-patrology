
import json
from lxml import etree


PARSER = etree.XMLParser(recover=True)
RE_REF_DETECT = r'([0-9]+-)?([A-Z]*[a-z]+-)*[A-Z][a-z]+_[0-9]+_[0-9]+'


def parse_tree(fpath):
    with open(fpath) as f:
        tree = etree.fromstring(
            f.read().replace('</>', ''),
            parser=PARSER)
    return tree


def read_mapping(path):
    mapping = {}
    with open(path) as f:
        for line in f:
            if line.startswith('?') or line.startswith('#'):
                continue
            a, b = line.strip().split('\t' if '\t' in line else ' ')
            if a in mapping:
                raise ValueError("Duplicate entry in mapping file", a)
            mapping[a] = b
    return mapping


def decode_ref(ref):
    book, chapter, verse = ref.split('_')
    book = ' '.join(book.split('-'))
    return book, chapter, verse


def encode_ref(ref):
    book, chapter, verse = ref
    return '-'.join(book.split()) + '_' + '_'.join([chapter, verse])


def read_vrt(path, fields=('pos', 'tt', 'pie')):
    with open(path) as f:
        for line in f:
            try:
                token, *data = line.strip().split('\t')
                if len(data) != len(fields):
                    raise ValueError(
                        "Expected {} metadata fields, but got {}. File: {}"
                        .format(len(fields), len(data), path))
                yield tuple([token] + data)
            except ValueError as e:
                raise e
            except Exception:
                print(line)


def read_refs(path):
    with open(path) as f:
        return json.load(f)


def read_doc(path):
    *path, ext = path.split('.')
    if ext != 'txt':
        raise ValueError("input file must be a .txt file")
    path = '.'.join(path)
    text = list(read_vrt('.'.join([path, 'txt'])))
    refs = read_refs('.'.join([path, 'refs.json']))

    return text, refs


def read_vulgate_lines(path='output/vulgate.csv'):
    with open(path) as f:
        for line in f:
            yield line.strip().split('\t')


def read_vulgate(fields=('pos', 'tt', 'pie'), **kwargs):
    vulgate, verses = [], {}
    cur = 0
    for book, chapter, verse_num, verse, *data in read_vulgate_lines(**kwargs):
        if len(data) != len(fields):
            raise ValueError("Expected {} metadata fields".format(len(fields)))
        verse = {'token': verse.split()}
        for field, data in zip(fields, data):
            verse[field] = data.split()
        vulgate.append(verse)
        verses[book, chapter, verse_num] = cur
        cur += 1
    return vulgate, verses