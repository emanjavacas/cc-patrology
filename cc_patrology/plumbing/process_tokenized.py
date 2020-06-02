
import re
import os
import glob
import json

from . import utils
from . import tagging


def read_tokens(text):
    for line in text.strip().split('\n'):
        if not line:
            continue
        try:
            token, pos, lemma = line.split('\t')
            yield token, pos, lemma
        except Exception as e:
            raise e


def extract_text(text, tag, ntokens):
    refs, output = [], []
    tokens, anchor = list(read_tokens(text)), 0
    while tokens:
        token, pos, lemma = tokens.pop(0)
        if re.match(utils.RE_REF_DETECT, token):
            ref = {'ref': token, 'anchor': anchor + ntokens}
            if tag == 'i' and anchor != 0:
                # find scope
                ref['scope'] = ntokens
            refs.append(ref)
        else:
            output.append((token, pos, lemma))
            anchor += 1

    return output, refs, anchor


def read_text(f_or_tree):
    output, refs, ntokens = [], [], 0

    if isinstance(f_or_tree, str):
        tree = utils.parse_tree(f_or_tree)
    else:
        tree = f_or_tree

    text = tree.xpath('//text')[0]
    for it in text.iterdescendants():
        if it.text:
            output_, refs_, ntokens_ = extract_text(it.text, it.tag, ntokens)
            output += output_
            refs += refs_
            ntokens += ntokens_
        if it.tail:
            output_, refs_, ntokens_ = extract_text(it.tail, it.tag, ntokens)
            output += output_
            refs += refs_
            ntokens += ntokens_

    return output, refs


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='output/tokenized')
    parser.add_argument('--target', default='output/plain')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--sent-len', default=25, type=int)
    parser.add_argument('--batch_size', default=20, type=int)
    parser.add_argument('--pie-path')
    args = parser.parse_args()

    piemodel = None
    if args.pie_path:
        import pie
        piemodel = pie.SimpleModel.load(args.pie_path)
        piemodel.to(args.device)

    for f in glob.glob('{}/*/*'.format(args.source)):
        tree = utils.parse_tree(f)
        text, refs = read_text(tree)

        # crete dirs
        *_, dirname, fname = f.split('/')
        dirname = os.path.join(args.target, dirname)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        # add pie lemmas if needed
        token, *_ = zip(*text)
        if piemodel is not None:
            lemmas = tagging.lemmatize_pie_batch(
                piemodel, tagging.segment_input(token, args.sent_len),
                bsize=args.batch_size, device=args.device, input_type='text')
            text = [(*tup, lem) for tup, lem in zip(text, lemmas)]

        # dump text
        fname = '{}.{}'.format('.'.join(fname.split('.')[:-1]), 'txt')
        with open(os.path.join(dirname, fname), 'w') as f:
            for line in text:
                f.write('\t'.join(line) + '\n')

        # dump refs
        refname = '.'.join(fname.split('.')[:-1]) + '.refs.json'
        with open(os.path.join(dirname, refname), 'w') as f:
            json.dump(refs, f)
