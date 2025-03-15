#!/usr/bin/env bash
# shellcheck disable=SC2128
SOURCED=false && [ "$0" = "$BASH_SOURCE" ] || SOURCED=true

#################### CLI
help="
Usage: download.sh [-d] [-v] [-o OUTPUT_BASE] [-a ALGORITHM]
                   [-e FILTER_REGEX] [-f FILTER_FIXED]
                   [-s FILTER_STRING]
                   PROJECT DATE
       download.sh (-h | -V)

Options:
      -d, --debug               Generate debug output (implies --verbose).
      -v, --verbose             Generate verbose output.
      -o, --output-base OUTPUT_BASE
                                Base output directory, downloaded will be
                                downloaded to OUTPUT_BASE/PROJECT/DATE/
                                [default: dumps].
      -e, --filter-regex FILTER_REGEX
                                Filter files names using a regular expression.
      -f, --filter-fixed FILTER_FIXED
                                List of files to download.
      -s, --filter-string FILTER_STRING
                                Filter files names searching for a string.
      -a, --algorithm ALGORITHM
                                Checksum algorithm, choose {md5, sha1}
                                [default: md5].
      -h, --help                Show this help message and exits.
      -V, --version             Print version and copyright information.
----
download.sh is part of wikidump.
download.sh needs docopts (v. 0.6.4) for CLI argument parsing.
"
version='version 0.3'

eval "$(docopts -A args -V "$version" -h "$help" : "$@")"
####################

#################### Helpers
declare -A filter_types

filter_types["-s"]="string"
filter_types["-e"]="regex"
filter_types["-f"]="fixed"

function get_last_filter {
    local args_clone=("${@:2}")
    filter_option=""
    filter=""
    for i in ${!args_clone[@]}; do
        opt="${args_clone[$i]}"
        opt_arg="${args_clone[$((i+1))]}"
        case "$opt" in
            -e|--filter-regex|-f|--filter-fixed|-s|--filter-string)
                filter_option="$opt"
                filter_type="${filter_types[$filter_option]}"
                filter="$opt_arg"
                shift 1
                ;;
            *)
                shift
                ;;
        esac
    done
}

function check_date_format {
    local input="$1"

    # Check if input is 'latest'
    if [[ "$input" == 'latest' ]]; then
        return 0  # Valid
    fi

    # Check if input matches the YYYYMMDD pattern
    if [[ "$input" =~ ^[0-9]{8}$ ]]; then
        # Validate if it's a real date (YYYYMMDD)
        if date -d "${input:0:4}-${input:4:2}-${input:6:2}" >/dev/null 2>&1; then
            return 0  # Valid
        else
            return 1  # Invalid date
        fi
    fi

    return 1  # Invalid format
}
####################

#################### Utils
if ${args['--debug']}; then
  # --debug implies --verbose
  verbose=true
  function echodebug {
    (echo "$@" | ts '[%F %H:%M:%S][debug]:' 1>&2)
  }
else
  function echodebug { true; }
fi

if ${args['--verbose']}; then
  function echoverbose {
    (echo "$@" | ts '[%F %H:%M:%S][info]:' 1>&2)
  }
else
  function echoverbose { true; }
fi

####################

echodebug "Program start"
echodebug "CLI args"
echodebug "--------"
for i in "${!args[@]}"; do
    echodebug "  - $i:" ${args[$i]};
done
echodebug ""

# CLI arguments
project="${args['PROJECT']}"
ddate="${args['DATE']}"

if ! check_date_format "$ddate"; then
    (echo "Error. Invalid date format, can be YYYYMMDD or 'latest'" 1>&2)
    exit 1
fi

tmpdir=$(mktemp -d -t download_sh.XXXXXXXXXX)
function cleanup {
  rm -rf "$tmpdir"
}
trap cleanup EXIT


# CLI options
output_base="${args['--output-base']}"
output_dir="$output_base/$project/$ddate"

get_last_filter "$@"
echodebug "filter_type: $filter_type"
echodebug "filter: $filter"

echoverbose
echoverbose "--- Download info ---"
echoverbose "  * Project: $project"
echoverbose "  * Date: $ddate"
echoverbose "  * Output directory: $output_dir"
echoverbose "  * Filter type: $filter_type"
echoverbose "  * Filter: $filter"
echoverbose

# dump base URL
BASE_URL="https://dumps.wikimedia.org/$project/$ddate"

# download the checksums file
#
# checksum file: <project>-<date>-{md5,sha1}sums.txt
# Example
#   - https://dumps.wikimedia.org/itwiki/20151002/
#       itwiki-20151002-md5sums.txt
algorithm="${args['--algorithm']}"
checksum_file="${project}-${ddate}-${algorithm}sums.txt"
echodebug "checksum_file: $checksum_file"

checksum_url="${BASE_URL}/${checksum_file}"
echoverbose
echoverbose "Dowloading MD5 sums file $checksum_url ..."
echoverbose

aria2c "$checksum_url"

# download the dump files

# create output_dir and all the necessary intermediate directories
mkdir -p "$output_dir"

selected_list=${tmpdir}/selected.txt
if [[ "$filter_type" == 'regex' ]]; then
    grep -E "$filter" "$checksum_file" > "$selected_list"
elif [[ "$filter_type" == 'fixed' ]]; then
    grep -F "$filter" "$checksum_file" > "$selected_list"
elif [[ "$filter_type" == 'string' ]]; then
    grep "$filter" "$checksum_file" > "$selected_list"
else
    (echo "Error. Invalid filter type, can be 'regex', 'fixed' or "
          "'string'" 1>&2)
    exit 1
fi

# prepare download list
download_list=${tmpdir}/download.txt
cut -f 3 -d ' ' "$selected_list" | \
    awk -v base=$BASE_URL '{print base"/"$0}' > "$download_list"

aria2c --max-concurrent-downloads 1 \
       --deferred-input \
       --dir="$output_dir" \
       --input-file "$download_list"

exit 0