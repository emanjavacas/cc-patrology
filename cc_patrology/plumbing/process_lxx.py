
import unicodedata
from cltk.tokenize.greek.word import GreekPunktWordTokenizer
from cc_patrology.utils import read_mapping
import requests

from . import tagging


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='output/lxx.raw.csv')
    parser.add_argument('--target', default='output/lxx.csv')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--pie-lemma-path')
    parser.add_argument('--pie-pos-path')
    args = parser.parse_args()

    # https://github.com/eliranwong/LXX-Swete-1930/blob/master/00-Swete_versification.csv
    verse_url = "https://raw.githubusercontent.com/eliranwong/LXX-Swete-1930/master/00-Swete_versification.csv"

    # https://github.com/eliranwong/LXX-Swete-1930/raw/master/01-Swete_word_with_punctuations.csv
    text_url = "https://raw.githubusercontent.com/eliranwong/LXX-Swete-1930/master/01-Swete_word_with_punctuations.csv"

    mapping = read_mapping('lxx.mapping')
    tok = GreekPunktWordTokenizer()

    verses = requests.get(verse_url).text
    verses = [tuple(row.strip().split('\t')) for row in verses.strip().split('\n')]
    def parse_ref(s):
        book, rest = s.split('.')
        chapter, verse = rest.split(':')
        return mapping[book], chapter, verse
    verses = [(int(w_id), parse_ref(rest)) for w_id, rest in verses]
    text = requests.get(text_url).text
    words = [tuple(row.strip().split('\t')) for row in text.strip().split('\n')]
    words = [(int(w_id), *(rest or [' '])) for w_id, *rest in words]

    with open('output/lxx.raw.csv', 'w+') as f:
        for (i, verse_id), (j, _) in zip(verses, verses[1:] + [(len(words) + 1, None)]):
            text = words[i-1: j-1]
            _, text = zip(*text)
            text = ' '.join(tok.tokenize(' '.join(text)))
            text = unicodedata.normalize('NFC', text)
            f.write('\t'.join(list(verse_id) + [text]) + '\n')
