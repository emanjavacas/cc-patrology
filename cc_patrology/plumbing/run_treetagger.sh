
SOURCE="output/formatted"
TARGET=$1
TTDIR=$2

MSG="bash run_treetagger.sh target/path treetagger/path"
[ -z "$TARGET" ] && { echo $MSG; exit 1; }
[ -z "$TTDIR" ] && { echo $MSG; exit 1; }
[ ! -d "$SOURCE" ] && { echo "$SOURCE doesn't exist!"; exit 1; }
[ ! -d "$TARGET" ] && mkdir -p "$TARGET"

# treetagger options
BIN="$TTDIR/bin"
CMD="$TTDIR/cmd"
LIB="$TTDIR/lib"

OPTIONS="-token -lemma -sgml -cap-heuristics"
# OPTIONS="-token -lemma -sgml"
TOKENIZER=${CMD}/utf8-tokenize.perl
MWL=${CMD}/mwl-lookup.perl
TAGGER=${BIN}/tree-tagger
PARFILE=${LIB}/latin.par
MWLFILE=${LIB}/latin-mwls
ABBR_LIST=latin.abbrv


for f in $SOURCE/*/*xml; do
    # variables
    DIR=$(dirname -- "$f")
    AUTHOR=$(basename -- "$DIR")
    FILE=$(basename -- "$f")

    # set up target dir
    [ ! -d "$TARGET/$AUTHOR" ] && mkdir -p "$TARGET/$AUTHOR"

    # tokenize
    cat $f | $TOKENIZER -a $ABBR_LIST |
    	# recognition of MWLs
    	$MWL -f $MWLFILE |
    	# tag
    	$TAGGER $OPTIONS $PARFILE |
	# remap <unknown>
	sed -e 's/<unknown>/$unk$/g' > $TARGET/$AUTHOR/$FILE
done
