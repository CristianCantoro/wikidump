#!/usr/bin/env bash

help="
Usage: download.sh [-f FILTER] [-l LIST] [-n] [-o OUTDIR] [-v] -d DATE PROJECT
       download.sh [-v] --md5-only -d DATE PROJECT
       download.sh (-h | --help)

Options:
      -d, --date DATE           Dump date (format: yyyymmdd).
      -f, --filter FILTER       Filter files names to download (defult: 'history').
      -l, --list LIST           List of files to download (default: download MD5 file).
                                (implies --md5-no-download)
      --md5-only                Only download the MD5 sums file.
      -n, --md5-no-download     Do not download the MD5 sums file.
      -o, --output-dir OUTDIR   Output directory for dump files.
      -v, --verbose             Generate verbose output.
      -h, --help                Show this help message and exits.
      --version                 Print version and copyright information.
----
download.sh is part of wikidump.
download.sh needs docopts for CLI argument parsing.
"
version='0.2'

eval "$(docopts -A args -h "$help" : "$@")"

echo "The keys are: " ${!args[@]}
echo "The values are: " ${args[@]}
echo " "
echo "Key <-> Value"
echo "-------------"
for i in "${!args[@]}"; do echo $i "<->" ${args[$i]}; done
echo " "

# CLI arguments
PROJECT="${args['PROJECT']}"

DATE="${args['--date']}"
if [ -z "$DATE" ]; then
    DATE='last'
fi

output_dir="${args['--output-dir']}"
OUTDIR="$output_dir/$PROJECT/$DATE"
if [ -z "$output_dir" ]; then
    OUTDIR="dumps/$PROJECT/$DATE"
fi

LIST="${args['--list']}"
md5_no_download=false
if [ -z "$LIST" ]; then
    md5_no_download=true
fi

FILTER="${args['--filter']}"
if [ -z "$FILTER" ]; then
    FILTER="history"
fi


if ${args['--verbose']}; then
    echo "--- Download info ---"
    echo "  * PROJECT: $PROJECT"
    echo "  * DATE: $DATE"
    echo "  * OUTDIR: $OUTDIR"
    echo "  * LIST: $LIST"
    echo "  * FILTER: $FILTER"
    echo "  "
    echo "  - md5_no_download: $md5_no_download"
    echo "---"
fi

# global base URL
BASE_URL="https://dumps.wikimedia.org/$PROJECT/$DATE/"

# download the md5sum
# https://dumps.wikimedia.org/itwiki/20151002/itwiki-20151002-md5sums.txt
if $md5_no_download; then
    if $verbose; then
        echo ""
        echo "Skipping MD5 download"
        echo ""
    fi
else
    MD5FILE="$PROJECT-$DATE-md5sums.txt"

    if $verbose; then
        echo ""
        echo "Dowloading MD5 sums file $BASE_URL/$MD5FILE ..."
        echo ""
    fi

    aria2c "$BASE_URL/$MD5FILE"

    if [ ! -z "$md5_only" ]; then
        echo ""
        echo "---"
        echo "Dowloading MD5 sums done!"
        exit 0
    fi
    LIST="$MD5FILE"
fi

# create OUTDIR and all the necessary intermediate directories
mkdir -p "$OUTDIR"


set -x
cut -f 3 -d ' ' "$LIST" | grep "$FILTER" | \
  awk -v prefix=$BASE_URL '{print prefix $0}' | \
  xargs -n 1 aria2c -x 3 -s 3 -c --force-sequential --dir="$OUTDIR"

exit 0
