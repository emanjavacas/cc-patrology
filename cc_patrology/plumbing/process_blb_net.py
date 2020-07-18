

import re
import json

from cc_patrology.utils import read_mapping


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='output/blb-net.json')
    parser.add_argument('--target', default='output/blb.net.csv')
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    from . import tagging
    from .process_blb_lxx import get_verses
    from stanfordcorenlp import StanfordCoreNLP
    # java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -annotators "tokenize,ssplit,pos,lemma" -port 9000 -timeout 30000

    nlp = StanfordCoreNLP('http://localhost', port=9000, timeout=30000)
    mapping = read_mapping('blb.mapping')

    verses = get_verses(args.source, mapping)

    with open(args.target, 'w') as f:
        for (book, chapter, verse_id), verse in verses.items():
            line = [book, chapter, verse_id]
            # need to strip "word.word" sequences because ttagger fails
            verse = re.sub('([a-z]+)\.([a-zA-Z])', r'\1. \2', verse)
            # tree-tagger
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
