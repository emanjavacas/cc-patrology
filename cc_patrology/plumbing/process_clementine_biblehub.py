
from . import tagging

def process_text(s):
    return s.replace("æ", "ae").replace("ji", "i").replace("j", "i").replace("J", "I")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='output/clementine.raw.csv')
    parser.add_argument('--target', default='output/clementine.csv')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--abbrev', default='latin.abbrv')
    parser.add_argument('--pie-path')
    parser.add_argument('--treetagger-dir')
    args = parser.parse_args()

    # set models
    piemodel = ttmodel = None
    if args.pie_path:
        import pie
        piemodel = pie.SimpleModel.load(args.pie_path)
        piemodel.to(args.device)
    if args.treetagger_dir:
        import treetaggerwrapper
        ttmodel = treetaggerwrapper.TreeTagger(
            TAGDIR=args.treetagger_dir,
            TAGLANG='la',
            TAGOPT='-token -lemma -sgml -quiet -cap-heuristics',
            # TAGINENCERR='strict',
            TAGABBREV=args.abbrev)

    with open(args.source) as inp, open(args.target, 'w') as f:
        for line in inp:
            book, chapter, verse_id, verse = line.strip().split('\t')
            verse = process_text(verse)
            line = [book, chapter, verse_id, verse]
            # tree-tagger
            if ttmodel is not None:
                data = tagging.process_treetagger(ttmodel, verse)
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
