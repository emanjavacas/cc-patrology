
import tqdm
import collections
import os

from lxml import etree

from . import tagging


def get_doc_id(tree):
    return tree.find('//div1').attrib['n'] + '-' + tree.find('//div2').attrib['n']


def get_verses(tree):
    elems = tree.xpath('//*[local-name() = "s" or local-name() = "milestone"]')
    for idx, (milestone, s) in enumerate(zip(elems[::2], elems[1::2])):
        try:
            assert milestone.tag == 'milestone', milestone.tag
            assert s.tag == 's', s.tag
            assert idx + 1 == int(milestone.attrib['n']), \
                (idx + 1, milestone.attrib['n'])
            yield idx + 1, ' '.join(s.text.split())
        except Exception as e:
            print(e)


def read_vulgate(path='vulgate/source', remove_chars='%;*'):
    by_doc_id = collections.defaultdict(dict)
    for f in os.listdir(path):
        if not f.endswith('xml'):
            continue
        with open(os.path.join(path, f)) as fn:
            tree = etree.fromstring(fn.read().encode('utf-8')).getroottree()
        doc_id = get_doc_id(tree)
        for idx, verse in get_verses(tree):
            # some verses are missing from the original...
            if verse == '[]':
                continue

            processed = []
            for w in verse.split():
                w_ = w
                for char in remove_chars:
                    w_ = w_.replace(char, '')
                if not w_:
                    w_ = w
                processed.append(w_)
            by_doc_id[doc_id][idx] = ' '.join(processed)

    return by_doc_id


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='vulgate/source')
    parser.add_argument('--target', default='output/vulgate.csv')
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

    with open(args.target, 'w') as f:
        for doc_id, verses in tqdm.tqdm(list(read_vulgate(path=args.source).items())):
            book, chapter = doc_id.split('-')
            for verse_id, verse in verses.items():
                line = [book, chapter, str(verse_id), verse]
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
