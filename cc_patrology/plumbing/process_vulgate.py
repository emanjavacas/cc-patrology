
import tqdm
import collections
import os

from lxml import etree


def get_doc_id(tree):
    return tree.find('//div1').attrib['n'] + '-' + tree.find('//div2').attrib['n']


def get_verses(tree, f):
    for milestone in tree.xpath('//*[local-name() = "milestone"]'):
        if not milestone.tail.strip():
            s = milestone.getnext()
            assert s.tag == 's', s.tag
            text = s.text
        else:
            text = milestone.tail

        assert text

        yield milestone.attrib['n'], ' '.join(text.strip().split())


def read_vulgate(path='output/vulgate/source', remove_chars='%;*'):
    by_doc_id = collections.defaultdict(dict)
    for f in os.listdir(path):
        if not f.endswith('xml'):
            continue
        with open(os.path.join(path, f)) as fn:
            tree = etree.fromstring(fn.read().encode('utf-8')).getroottree()
        doc_id = get_doc_id(tree)
        for idx, verse in get_verses(tree, f):
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
    parser.add_argument('--source', default='output/vulgate/source')
    parser.add_argument('--target', default='output/vulgate.csv')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--abbrev', default='latin.abbrv')
    parser.add_argument('--pie-path')
    parser.add_argument('--treetagger-dir')
    args = parser.parse_args()

    from cc_patrology.plumbing import tagging

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
                line = [book, chapter, str(verse_id)]
                # tree-tagger
                if ttmodel is not None:
                    data = tagging.process_treetagger(ttmodel, verse)
                    verse = ' '.join(data['token'])  # and use it for other lemmatizer
                    line.append(' '.join(verse))
                    lemmas, pos = data['lemma'], data['pos']
                    lemmas = [lem if lem != '<unknown>' else '$unk$' for lem in lemmas]
                    line.append(' '.join(pos))
                    line.append(' '.join(lemmas))
                    assert len(verse.split()) == len(lemmas) == len(pos)
                # pie lemmatizer
                if piemodel is not None:
                    lemmas = tagging.lemmatize_pie(
                        piemodel, verse.split(), device=args.device)
                    line.append(' '.join(lemmas))
                    assert len(lemmas) == len(verse.split())

                f.write('\t'.join(line) + '\n')
