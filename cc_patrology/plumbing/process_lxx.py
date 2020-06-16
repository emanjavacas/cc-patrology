
from cltk.tokenize.greek.word import GreekPunktWordTokenizer
import unicodedata
import requests
import pie

from cc_patrology.utils import read_mapping
from . import tagging


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='output/lxx.csv')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--use-beam', action='store_true')
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

    lemma_model = pie.SimpleModel.load(args.pie_lemma_path)
    pos_model = pie.SimpleModel.load(args.pie_pos_path)
    lemma_model.to(args.device)
    pos_model.to(args.device)

    with open(args.target, 'w+') as f:
        for (i, verse_id), (j, _) in zip(verses, verses[1:] + [(len(words) + 1, None)]):
            text = words[i-1: j-1]
            _, text = zip(*text)
            text = ' '.join(tok.tokenize(' '.join(text)))
            text = unicodedata.normalize('NFC', text)
            if text:
                lemma = tagging.lemmatize_pie(
                    lemma_model, text.split(), input_type='sent', device=args.device,
                    use_beam=args.use_beam)
                pos = tagging.postag_pie(
                    pos_model, text.split(), input_type='sent', device=args.device)
                lemma = ' '.join(lemma)
                pos = ' '.join(pos[0])
            else:
                lemma = pos = ' '
            f.write('\t'.join(list(verse_id) + [text, pos, lemma]) + '\n')
