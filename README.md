
CC-PATROLOGY
---

Scripts to process CC xml (e.g. Patrology), doing:
	- Text cleanup
    - Reference parsing (II Cor, IV 2) -> (2-Cor, 4, 2)
	- Morphological tagging with TreeTagger and PIE
	- Utility functions

It also downloads the Bible from Perseus and processes and tags it.

After running `run.py`, there are a bunch of utility in function inside
`cc_patrology.utils` to load the processed documents.

# Requirements

- `Treetagger` should be installed somewhere on your system and you'll need the path
to that installation to run `run.py`.
- An installation of `pie`: `pip install nlp-pie` should do it. There is a pie model
in the repository that can be used to tag medieval latin.

