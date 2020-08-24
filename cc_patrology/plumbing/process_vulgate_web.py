
from lxml import etree
import requests

from cc_patrology.utils import read_mapping


def get_tree():
    r = requests.request(
        'GET',
        'http://www.perseus.tufts.edu/hopper/dltext?doc=Perseus%3Atext%3A1999.01.0156')

    tree = etree.fromstring(r.content)

    return tree


def get_text(item):
    output = ''
    if item.text is not None:
        output += item.text
    if item.tail is not None:
        output += item.tail
    for child in item.getchildren():
        if child.tag == 'milestone':
            return output
        for text in child.itertext(with_tail=True):
            output += text
        if child.tail is not None:
            output += child.tail
    return output


def get_text_tail(item):
    output = item.tail
    for sibling in item.itersiblings():
        if sibling.tag == 'milestone':
            return output
        for text in sibling.itertext(with_tail=True):
            output += text
    return output

def read_verses():
    tree = get_tree()
    verses = {}
    for book in tree.xpath('//div1'):
        head, *chapters = book.getchildren()
        title = book.attrib['n'].strip()
        for chapter in chapters:
            chapter_id = chapter.attrib['n']
            for verse in chapter.iterdescendants():
                if verse.tag != 'milestone':
                    continue
                next_it = verse.getnext()
                if next_it is not None and next_it.tag == 'p':
                    text = get_text(next_it)
                elif verse.tail:
                    text = get_text_tail(verse)
                else:
                    # milestone inside p with following p
                    assert (verse.getparent().tag == 'p' and
                            verse.getparent().getnext().tag == 'p')
                    text = get_text(verse.getparent().getnext())
                if not text.strip():
                    print("empty", title, chapter_id, verse_id)
                verse_id = verse.attrib['n']
                text = ' '.join(text.strip().split())
                verses[title, chapter_id, verse_id] = text

    return verses


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='output/vulgate.web.csv')
    args = parser.parse_args()
    from . import tagging
    from stanfordcorenlp import StanfordCoreNLP
    # java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -annotators "tokenize,ssplit,pos,lemma" -port 9000 -timeout 30000

    nlp = StanfordCoreNLP('http://localhost', port=9000, timeout=30000)
    mapping = read_mapping('web.mapping')

    with open(args.target, 'w') as f:
        for (book, chapter, verse_id), verse in read_verses().items():
            book = mapping[book]
            line = [book, chapter, verse_id]
            if not verse:
                print("missing", book, chapter, verse_id)
                continue
            data = tagging.process_standford(nlp, verse)
            verse = ' '.join(data['token'])  # and use it for other lemmatizer
            line.append(verse)       # use treetagger tokenization
            lemmas, pos = data['lemma'], data['pos']
            lemmas = [lem if lem != '<unknown>' else '$unk$' for lem in lemmas]
            line.append(' '.join(pos))
            line.append(' '.join(lemmas))
            f.write('\t'.join(line) + '\n')
