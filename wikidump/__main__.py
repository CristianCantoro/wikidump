"""Main module that parses command line arguments."""
import os
import io
import bz2
import gzip
import sys
import codecs
import argparse
import subprocess

import mw.xml_dump
import mwxml
import pathlib
from typing import IO, Optional, Union

from . import processors, utils


def open_xml_file(path: Union[str, IO]):
    """Open an xml file, decompressing it if necessary."""
    f = mw.xml_dump.functions.open_file(
        mw.xml_dump.functions.file(path)
    )
    return f


def compressor_7z(file_path: str):
    """"Return a file-object that compresses data written using 7z."""
    p = subprocess.Popen(
        ['7z', 'a', '-si', file_path],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )
    return io.TextIOWrapper(p.stdin, encoding='utf-8')


def output_writer(path: str, compression: Optional[str]):
    """Write data to a compressed file."""
    if compression == '7z':
        return compressor_7z(path + '.7z')
    if compression == 'bz2':
        return bz2.open(path + '.bz2', 'wt', encoding='utf-8')
    elif compression == 'gzip':
        return gzip.open(path + '.gz', 'wt', encoding='utf-8')
    else:
        return open(path, 'wt', encoding='utf-8')


def create_path(path: Union[pathlib.Path, str]):
    """Create a path, which may or may not exist."""
    path = pathlib.Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True)


def get_args():
    """Parse command line arguments."""
    ERR_NO_FILES = 1
    ERR_NO_FUNC = 2

    parser = argparse.ArgumentParser(
        prog='wikidump',
        description='Wikidump features extractor.',
    )
    parser.add_argument(
        'files',
        metavar='FILE',
        type=pathlib.Path,
        nargs='*',
        help='XML Wikidump file to parse. It accepts 7z or bzip2.',
    )
    parser.add_argument(
        '--output-dir',
        type=pathlib.Path,
        default=pathlib.Path('output'),
        help='Output directory for processed results [default: ./output].',
    )
    parser.add_argument(
        '--output-compression',
        choices={None, '7z', 'bz2', 'gzip'},
        required=False,
        default=None,
        help='Output compression format [default: None].',
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help="Don't write any file",
    )

    subparsers = parser.add_subparsers(help='sub-commands help')
    processors.bibliography_extractor.configure_subparsers(subparsers)
    processors.identifiers_extractor.configure_subparsers(subparsers)
    processors.identifiers_history_extractor.configure_subparsers(subparsers)
    processors.page_ids_extractor.configure_subparsers(subparsers)
    processors.redirect_extractor.configure_subparsers(subparsers)
    processors.revisionlist_extractor.configure_subparsers(subparsers)
    processors.sections_counter.configure_subparsers(subparsers)
    processors.wikilink_extractor.configure_subparsers(subparsers)

    parsed_args = parser.parse_args()
    if 'func' not in parsed_args:
        parser.print_usage()
        print('Error: no processor provided.', file=sys.stderr)
        parser.exit(ERR_NO_FUNC)

    if len(parsed_args.files) == 0:
        parser.print_usage()
        print('Error: no file provided.', file=sys.stderr)
        parser.exit(ERR_NO_FILES)

    return parsed_args


def main():
    """Main function."""
    args = get_args()

    if not args.output_dir.exists():
        args.output_dir.mkdir(parents=True)

    for input_file_path in args.files:
        utils.log("Analyzing {}...".format(input_file_path))

        dump = mwxml.Dump.from_file(open_xml_file(str(input_file_path)))

        basename = input_file_path.name

        if args.dry_run:
            pages_output = open(os.devnull, 'wt')
            stats_output = open(os.devnull, 'wt')
        else:
            pages_output = output_writer(
                path=str(args.output_dir/(basename + '.features.xml')),
                compression=args.output_compression,
            )
            stats_output = output_writer(
                path=str(args.output_dir/(basename + '.stats.xml')),
                compression=args.output_compression,
            )
        args.func(
            dump,
            pages_output,
            stats_output,
            args,
        )

        # dump is not a file-like object, cannot explictly close input file
        # dump.close()

        # explicitly close output files
        pages_output.close()
        stats_output.close()

        utils.log("Done Analyzing {}.".format(input_file_path))


if __name__ == '__main__':
    main()
