
import json
import re
import os
import glob

from lxml import etree

from . import utils


RE_REF = (
    r"([ivcxl]+ )?"             # book num
    r"([a-z]+)"                 # book
    r" ?[\.,·]? ?[\.,·]? "
    r"([icvxl]+)"               # chapter
    r" ?[\.,·]? "
    r"(i?[0-9]+|[icvxl]+)\.?"   # verse
)

# Extract multiple refs
# - (Coloss. III, 1 , 2) Colossians_3_1
# - (Isai. XL, 6-8) Isaiah_40_6
# - (Matth . vi, 20 et 21) Matthew_6_20
# - ( Act, VII, 58. et 59) Acts_7_58
# - ( Psal. XXXVI, 10, 55, 36) Psalms_36_10
RE_REF_1 = r"et ([0-9]+|[icvxl]+)"
RE_REF_2 = r"- ?([1-9][0-9]*)"
RE_REF_3 = r"([\.,] ?([1-9][0-9]*))+"
RE_REF_COMPLEX = r"(?P<rest> ?[\.,]?{}".format(
    '(' + '|'.join([RE_REF_1, RE_REF_2, RE_REF_3]) + '))?')
RE_REF += RE_REF_COMPLEX


def normalize_whitespace(s):
    return ' '.join(s.strip().split())


def extract_plain_text(texts):
    if isinstance(texts, list):
        for text in texts:
            yield from extract_plain_text(text)
    else:
        for it in texts.iterdescendants():
            if it.text:
                yield from it.text.strip().split()
            if it.tail:
                yield from it.tail.strip().split()


def parse_refs(ref):
    """
    Try to parse a matched string and parse references.
    It may return None if the matched string cannot be parsed (false positive)
    It may return a tuple (single ref)
        or a list of refs if the underlying string contains several refs
    """

    # remove parentheses, lower and remove trailing space
    ref = ref.replace("(", "").replace(")", "").lower().strip()

    if ";" in ref:
        refs = ref.split(";")
        output = []
        for ref in refs:
            ref = ref.strip()
            ref = parse_refs(ref)
            if ref is not None:
                output.append(ref)
        return output

    m = re.match(RE_REF, ref)

    if m is not None:
        # base groups
        book_num, book, chapter, verse, *_ = [
            (g or '').strip() or None for g in m.groups()]

        # check rest
        rest = m.groupdict()['rest']

        if rest is not None:
            rest = rest.strip()
            tup = (book_num, book, chapter)

            # et
            if re.match(RE_REF_1, rest):
                new_verse = re.search(r"([0-9]+|[icvxl]+)", rest).group()
                return [tup + (verse,), tup + (new_verse,)]

            # hyphen range
            elif re.match(RE_REF_2, rest):
                if not verse.isdigit():
                    # assume mistake
                    return
                start, stop = int(verse), int(re.search(r"([0-9]+)", rest).group())
                # ignore spans larger than 15
                if start > stop or start == stop or stop - start > 15:
                    return
                output = []
                for verse in range(start, stop + 1):
                    output.append(tup + (str(verse), ))
                return output

            # comma separated
            elif re.match(RE_REF_3, rest):
                tup = (book_num, book, chapter)
                output = []
                output.append(tup + (verse,))
                for verse in re.finditer(r"([0-9]+|[icvxl]+)", rest):
                    output.append(tup + (verse.group(),))
                return output
            else:
                print('Warning, unmatched complex regex: "{}"'.format(rest))

        return book_num, book, chapter, verse


def roman_to_int(roman):
    values = {
        'M': 1000,
        'D': 500,
        'C': 100,
        'L': 50,
        'X': 10,
        'V': 5,
        'I': 1}

    roman = roman.upper()

    numbers = []
    for char in roman:
        numbers.append(values[char])

    if len(roman) == 1:
        return values[roman]

    total = 0
    for num1, num2 in zip(numbers, numbers[1:]):
        if num1 >= num2:
            total += num1
        else:
            total -= num1

    return total + num2


def extract_refs(m, book_mapping, bible_mapping, verses, verbose=True):
    refs = parse_refs(m.group())
    if not refs:
        return
    for ref in ([refs] if isinstance(refs, tuple) else refs):
        book_num, book, chapter, verse = ref
        book = book_mapping.get(book, book)
        book = bible_mapping.get(book, book)
        if book_num is not None:
            book = str(roman_to_int(book_num)) + ' ' + book
        chapter = str(roman_to_int(chapter))
        if (book, chapter, verse) in verses:
            yield (book, chapter, verse)
        else:
            if verbose:
                print("ignoring", m.group())


def format_refs(tree):
    text = tree.xpath('//text')[0]
    for item in text.iterdescendants():
        if item.text:
            itext = normalize_whitespace(item.text)
            ms = list(re.finditer(r'\(' + RE_REF + r'\)', itext.lower()))
            for m in ms[::-1]:
                refs = extract_refs(m, book_mapping, bible_mapping, verses)
                refs = ' '.join(utils.encode_ref(ref) for ref in refs)
                start, end = m.span()
                itext = itext[:start] + refs + itext[end:]
            item.text = itext
        if item.tail:
            itext = normalize_whitespace(item.tail)
            ms = list(re.finditer(r'\(' + RE_REF + r'\)', itext.lower()))
            for m in ms[::-1]:
                refs = extract_refs(m, book_mapping, bible_mapping, verses)
                refs = ' '.join(utils.encode_ref(ref) for ref in refs)
                start, end = m.span()
                itext = itext[:start] + refs + itext[end:]
            item.tail = itext

    return text


def extract_author(tree):
    author = tree.xpath('//bibl/author')
    author = ' '.join(name for name in author[0].text.strip().split('\n'))
    return author


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('source', default='path/to/directory')
    parser.add_argument('--target', default='output/formatted')
    parser.add_argument('--book-mapping', default='book.mapping')
    parser.add_argument('--bible-mapping', default='bible.mapping')
    args = parser.parse_args()

    if not os.path.isdir(args.target):
        os.makedirs(args.target)

    _, verses = utils.read_vulgate()
    book_mapping = utils.read_mapping(args.book_mapping)
    bible_mapping = utils.read_mapping(args.bible_mapping)

    for f in glob.glob(os.path.join(args.source, '*', '*.xml')):
        # load tree
        tree = utils.parse_tree(f)

        # reformat refs
        text = format_refs(tree)

        # create directory
        *_, author, fname = f.split('/')
        dirname = os.path.join(args.target, author)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        # dump tree
        with open(os.path.join(dirname, fname), 'w') as outf:
            outf.write(etree.tostring(text, encoding='utf8', pretty_print=True).decode())

        # dump meta
        author = extract_author(tree)
        refname = '.'.join(fname.split('.')[:-1]) + '.meta.json'
        with open(os.path.join(dirname, refname), 'w') as f:
            json.dump({'author': author}, f)
