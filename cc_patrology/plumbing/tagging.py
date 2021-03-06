
import json
import pie


def process_treetagger(model, sent):
    token, pos, lemma = zip(*[line.split('\t') for line in model.tag_text(sent)])
    return {'token': token, 'pos': pos, 'lemma': lemma}


def process_standford(nlp, sent):
    output = json.loads(nlp.annotate(
        sent, properties={'annotators': 'pos,lemma',
                          'pipelineLanguage': 'en',
                          'outputFormat': 'json'}))
    token, lemma, pos = [], [], []
    for s in output['sentences']:
        for w in s['tokens']:
            token.append(w['originalText'])
            lemma.append(w['lemma'])
            pos.append(w['pos'])
    return {'token': token, 'lemma': lemma, 'pos': pos}


def segment_input(text, sent_len):
    output = []
    for i in range(0, len(text), sent_len):
        output.append(list(text[i:i+sent_len]))

    assert len(text) == sum(len(s) for s in output)

    return output


def lemmatize_pie(model, sents, use_beam=False, beam_width=12, device='cpu',
                  input_type='sent'):

    if input_type == 'sent':
        sents = [sents]

    inp, _ = pie.data.pack_batch(model.label_encoder, sents, device=device)
    preds = model.predict(
        inp, "lemma", use_beam=use_beam, beam_width=beam_width
    )['lemma']

    fn = model.label_encoder.tasks['lemma'].preprocessor_fn
    if fn is not None:
        preds = [fn.inverse_transform(pred, tok)
                 for pred, tok in zip(preds, [w for sent in sents for w in sent])]

    return preds


def postag_pie(model, sents, device='cpu', input_type='sent'):

    if input_type == 'sent':
        sents = [sents]

    inp, _ = pie.data.pack_batch(model.label_encoder, sents, device=device)
    preds = model.predict(inp, "pos")['pos']

    return preds


def lemmatize_pie_batch(model, sents, bsize=25, **kwargs):
    output = []
    for batch in segment_input(sents, bsize):
        for lem in lemmatize_pie(model, batch, **kwargs):
            output.append(lem)
    return output
