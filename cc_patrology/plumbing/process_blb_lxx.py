
import unicodedata
from cltk.tokenize.greek.word import GreekPunktWordTokenizer
import re
import json

from cc_patrology.utils import read_mapping


def get_verses(path, target_bible, mapping):
    verses = {}
    with open('output/blb.json') as f:
        for line in f:
            chapter = json.loads(line.strip())
            url = chapter['url']
            bible = re.match(
                r"https://www.blueletterbible.org/([^/]+)/.*", url
            ).group(1)
            if bible != target_bible:
                continue
            for data in chapter['verses']:
                verse_id, verse = data
                assert verse.find(verse_id) >= 0
                _, *verse = verse.split('-')
                verse = '-'.join(verse)
                verse = verse.strip()
                if verse.startswith('See '):
                    continue
                if re.search(r'^[\[(][^\])]+[)\]]', verse):
                    verse = re.sub(r'^[\[(][^\])]+[)\]]', '', verse).strip()

                # verse id
                book, rest = verse_id.split()
                chapter, verse_id = rest.split(':')
                book = mapping[book]
                verse_id = book, chapter, verse_id
                if verse_id in verses:
                    assert verses[verse_id] == verse
                verses[verse_id] = verse

    return verses


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='output/blb.json')
    parser.add_argument('--target', default='output/blb.lxx.csv')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--pie-lemma-path')
    parser.add_argument('--pie-pos-path')
    args = parser.parse_args()

    import pie
    from . import tagging

    mapping = read_mapping('blb.mapping')

    verses = get_verses(args.source, 'lxx', mapping)

    # set models
    lemma_model = pie.SimpleModel.load(args.pie_lemma_path)
    pos_model = pie.SimpleModel.load(args.pie_pos_path)
    lemma_model.to(args.device)
    pos_model.to(args.device)
    tok = GreekPunktWordTokenizer()

    with open(args.target, 'w') as f:
        for (book, chapter, verse_id), verse in verses.items():
            line = [book, chapter, verse_id]
            text = ' '.join(tok.tokenize(verse))
            text = unicodedata.normalize('NFC', text)
            if text:
                lemma = tagging.lemmatize_pie(
                    lemma_model, text.split(), input_type='sent', device=args.device)
                pos = tagging.postag_pie(
                    pos_model, text.split(), input_type='sent', device=args.device)
                lemma = ' '.join(lemma)
                pos = ' '.join(pos[0])
            else:
                lemma = pos = ' '
            f.write('\t'.join([book, chapter, verse_id, text, pos, " ", lemma]) + '\n')
