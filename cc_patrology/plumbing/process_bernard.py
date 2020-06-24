
import json
import os
import re
import glob
from lxml import etree

from cc_patrology import utils

_, BIBLE = utils.read_vulgate()
MAPPING = utils.read_mapping('bernard.mapping')
NSMAP = {'tei': 'http://www.tei-c.org/ns/1.0',
         'w3': 'http://www.w3.org/XML/1998/namespace'}


def parse_file(fname):
    # /TEI/text/body/div[type="work"]/div[type="chapter" & n="1-..."]/
    # /p[style="txt_Normal"]
    with open(fname, 'r+') as f:
        tree = etree.fromstring(f.read().encode('utf-8'))

    return tree


def wrap_ns(ns, tag):
    return '{' + NSMAP[ns] + '}' + tag


def remove_ns(tag):
    return re.sub(r'{[^}]+}', '', tag)


def get_link_type(link):
    # there is a case where type is "inexactQuotation inexactQuotation"
    t = link.attrib.get('type').split()[0]
    allusion = link.attrib.get('ana')
    if allusion is not None:
        t += '-{}'.format('allusion')
    return t


def process_ref(ref):
    pref = ref.replace('\xa0', ' ')
    # collect refs
    book_chapter, verse = pref.split(',')
    *num, book, chapter = book_chapter.split(' ')
    book = MAPPING[book]
    if num:
        book = num[0] + '-' + book
    # Ph 1, 23. 22
    # Ps 147, 1-2
    verse = verse.replace(' ', '')  # drop spaces
    verses = []
    if '.' in verse:
        # Pr 31, 10. 19
        # these seem to refer to those specified verses
        # or specified verses and ranges: Lc 10, 30.33-34
        for part in verse.split('.'):
            if '-' in part:
                start, stop = part.split('-')
                start, stop = int(start), int(stop)
                assert stop > start
                verses.extend([str(v) for v in range(start, stop)])
            else:
                verses.append(str(int(part)))
    elif '-' in verse:
        # Ac 9, 36-41
        # these seem to refer to the specified range
        start, stop = verse.split('-')
        start, stop = int(start), int(stop)
        assert stop > start
        for verse in range(start, stop):
            verses.append(str(verse))
    else:
        verses.append(str(int(verse)))

    return [utils.encode_ref((book, chapter, verse)) for verse in verses]


def get_refs(tree):
    links = tree.xpath('//tei:link', namespaces=NSMAP)
    for link in links:
        if 'target' not in link.attrib:
            print("missing target", link.attrib)
            continue
        # extract ref type from link
        ref_type = get_link_type(link)

        # extract target words
        id1, id2 = link.attrib['target'].split()
        id1, id2 = id1.replace('#', ''), id2.replace('#', '')
        span = tree.xpath('//tei:span[@xml:id="{}"]'.format(id1), namespaces=NSMAP)
        if len(span) != 1:
            # span doesn't have info
            print("larger span")
            continue
        span = span[0]
        # this returns a tuple if the ref is specified as range
        if 'from' in span.attrib:
            start, stop = span.attrib['from'], span.attrib['to']
            start, stop = start.replace('#', ''), stop.replace('#', '')
            span = start, stop
        else:
            span = span.attrib['target'].replace('#', '')

        # extract ref
        seg = tree.xpath('//tei:seg[@xml:id="{}"]'.format(id2), namespaces=NSMAP)
        seg = seg[0]
        bibl = seg.findall('tei:bibl', namespaces=NSMAP)
        if len(bibl) != 1:
            # weird case
            print("bibl", len(bibl))
            continue
        bibl = bibl[0]
        # ptr = bibl.findall('tei:ptr', namespaces=NSMAP)
        # ptr = ptr[0]
        # cref = ptr.attrib['target']

        ref = bibl.findall('tei:ref', namespaces=NSMAP)
        ref = ref[0]
        # ref = ref.attrib.get('cRef', ref.text)
        ref = ref.text
        if ref is None:
            print("Emtpy ref")
            continue
        if 'etc' in ref:
            print("etc")
            continue
        try:
            ref = process_ref(ref)
        except Exception as e:
            print("cannot parse", ref, e)
            continue

        # record reference
        yield ref_type, span, ref


def get_token(w):
    w_id = w.attrib[wrap_ns('w3', 'id')]
    if remove_ns(w.tag) == 'w':
        return w_id, w.text, w.attrib['ana'], w.attrib['lemma']
    else:
        return w_id, w.text, 'PUN', w.text


def process_tree(tree):
    word_ids, words = {}, []
    for idx, w in enumerate(tree.xpath('//tei:w|//tei:pc', namespaces=NSMAP)):
        word_ids[w.attrib[wrap_ns('w3', 'id')]] = idx
        words.append(get_token(w))

    refs = []
    for ref_type, span, ref in get_refs(tree):
        if isinstance(span, tuple):
            # range
            start, stop = span
            start, stop = word_ids[start], word_ids[stop]
            assert stop >= start, (start, stop)
            if start == stop:
                source = [start]
            else:
                source = list(range(start, stop))
        else:
            # string
            source = list(map(word_ids.get, span.split()))

        target = []
        for r in ref:
            try:
                BIBLE[utils.decode_ref(r)]
                target.append(utils.decode_ref(r))
            except KeyError:
                print(r)

        refs.append({'ref_type': ref_type,
                     'span': span,
                     'target': target,
                     'source': source})

    return words, refs


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='output/bernard/')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--abbrev', default='latin.abbrv')
    parser.add_argument('--pie-path')
    parser.add_argument('--treetagger-dir')
    args = parser.parse_args()

    from cc_patrology.plumbing import tagging

    # set models
    piemodel = ttmodel = None
    import pie
    piemodel = pie.SimpleModel.load(args.pie_path)
    piemodel.to(args.device)
    import treetaggerwrapper
    ttmodel = treetaggerwrapper.TreeTagger(
        TAGDIR=args.treetagger_dir,
        TAGLANG='la',
        TAGOPT='-token -lemma -sgml -quiet -cap-heuristics',
        # TAGINENCERR='strict',
        TAGABBREV=args.abbrev)

    for idx, f in enumerate(glob.glob('./SCT1-5/*xml')):
        try:
            tree = parse_file(f)
        except Exception as e:
            continue

        words, refs = process_tree(tree)
        tokens = [w for _, w, _, _ in words]
        # tree-tagger
        data = tagging.process_treetagger(ttmodel, ' '.join(tokens))
        ttlemmas, ttpos = data['lemma'], data['pos']
        ttlemmas = [lem if lem != '<unknown>' else '$unk$' for lem in ttlemmas]
        # pie lemmatizer
        pielemmas = []
        for i in range(0, len(tokens), 500):
            # print(tokens[i:i+500])
            pielemmas.extend(tagging.lemmatize_pie(
                piemodel, tokens[i:i+500], device=args.device))
        assert len(ttlemmas) == len(ttpos) == len(words) == len(pielemmas)

        if not os.path.isdir(args.target):
            os.makedirs(args.target)
        source_path = '.'.join(
            os.path.join(args.target, os.path.basename(f)).split('.')[:-1])
        
        with open(source_path + '.txt', 'w') as f_out:
            for (w_id, token, pos, lemma), ttpos, ttlemma, pielemma in zip(
                    words, ttpos, ttlemmas, pielemmas):
                f_out.write('\t'.join([w_id, token, ttpos, ttlemma, pielemma]) + '\n')
        with open(source_path + '.refs.json', 'w') as f_out:
            json.dump(refs, f_out)
