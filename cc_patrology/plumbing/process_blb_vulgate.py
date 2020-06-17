
import re
import json

from cc_patrology.utils import read_mapping


mapping = read_mapping('blb.mapping')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='output/blb.json')
    parser.add_argument('--target', default='output/blb.vulgate.csv')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--abbrev', default='latin.abbrv')
    parser.add_argument('--pie-path')
    parser.add_argument('--treetagger-dir')
    args = parser.parse_args()
    from . import tagging

    # set models
    piemodel = ttmodel = None
    if args.pie_path:
        import pie
        piemodel = pie.SimpleModel.load(args.pie_path)
        piemodel.to(args.device)
    if not args.treetagger_dir:
        raise ValueError("Needs treetagger")
    import treetaggerwrapper
    ttmodel = treetaggerwrapper.TreeTagger(
        TAGDIR=args.treetagger_dir,
        TAGLANG='la',
        TAGOPT='-token -lemma -sgml -quiet -cap-heuristics',
        # TAGINENCERR='strict',
        TAGABBREV=args.abbrev)

    verses = {}
    with open(args.source) as f:
        for line in f:
            chapter = json.loads(line.strip())
            url = chapter['url']
            bible = re.match(
                r"https://www.blueletterbible.org/([^/]+)/.*", url
            ).group(1)
            if bible != 'vul':
                continue
            for data in chapter['verses']:
                verse_id, verse = data
                assert verse.find(verse_id) >= 0
                _, verse = verse.split('-')
                verse = verse.strip()

                # verse id
                book, rest = verse_id.split()
                chapter, verse_id = rest.split(':')
                book = mapping[book]
                verse_id = book, chapter, verse_id
                if verse_id in verses:
                    assert verses[verse_id] == verse
                verses[verse_id] = verse

    with open(args.target, 'w') as f:
        for (book, chapter, verse_id), verse in verses.items():
            line = [book, chapter, verse_id]
            # tree-tagger
            if ttmodel is not None:
                data = tagging.process_treetagger(ttmodel, verse)
                verse = ' '.join(data['token'])  # and use it for other lemmatizer
                line.append(verse)       # use treetagger tokenization
                lemmas, pos = data['lemma'], data['pos']
                lemmas = [lem if lem != '<unknown>' else '$unk$' for lem in lemmas]
                line.append(' '.join(pos))
                line.append(' '.join(lemmas))
            # pie lemmatizer
            if piemodel is not None:
                lemmas = tagging.lemmatize_pie(
                    piemodel, verse.lower().split(), device=args.device)
                line.append(' '.join(lemmas))
            f.write('\t'.join(line) + '\n')