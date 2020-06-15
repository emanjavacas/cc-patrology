
import pie


def process_treetagger(model, sent):
    token, pos, lemma = zip(*[line.split('\t') for line in model.tag_text(sent)])
    return {'token': token, 'pos': pos, 'lemma': lemma}


def segment_input(text, sent_len):
    output = []
    for i in range(0, len(text), sent_len):
        output.append(list(text[i:i+sent_len]))
    return output


def lemmatize_pie(model, sents, use_beam=True, beam_width=12, device='cpu',
                  input_type='sent'):

    if input_type == 'sent':
        sents = [sents]

    inp, _ = pie.data.pack_batch(model.label_encoder, sents, device=device)
    preds = model.predict(
        inp, "lemma", use_beam=use_beam, beam_width=beam_width
    )['lemma']

    fn = model.label_encoder.tasks['lemma'].preprocessor_fn
    if fn is not None:
        preds = [[fn.inverse_transform(pred, tok) for pred, tok in zip(preds, sent)]
                 for sent in sents]

    # flatten output
    preds = [tok for sent in sents for tok in preds]

    return preds


def postag_pie(model, sents, device='cpu', input_type='sent'):

    if input_type == 'sent':
        sents = [sents]

    inp, _ = pie.data.pack_batch(model.label_encoder, sents, device=device)
    preds = model.predict(inp, "pos")['lemma']

    # flatten output
    preds = [tok for sent in sents for tok in preds]

    return preds


def lemmatize_pie_batch(model, sents, bsize=25, **kwargs):
    output = []
    for batch in segment_input(sents, bsize):
        for lem in lemmatize_pie(model, batch, **kwargs):
            output.append(lem)
    return output
