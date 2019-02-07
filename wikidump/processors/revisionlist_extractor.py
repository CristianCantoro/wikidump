"""Extract all revisions for all pages.

The output format is csv.
"""

import csv
import collections
import datetime
import functools
import arrow

import fuzzywuzzy.process
import jsonable
import more_itertools
import mwxml
from typing import Iterable, Iterator, Mapping, NamedTuple, Optional

from .. import dumper, extractors, languages, utils


stats_template = '''
<stats>
    <performance>
        <start_time>${stats['performance']['start_time'] | x}</start_time>
        <end_time>${stats['performance']['end_time'] | x}</end_time>
        <revisions_analyzed>${stats['performance']['revisions_analyzed'] | x}</revisions_analyzed>
        <pages_analyzed>${stats['performance']['pages_analyzed'] | x}</pages_analyzed>
    </performance>
</stats>
'''


csv_output_fields = ['page_id',
                     'page_title',
                     'revision_id',
                     'revision_parent_id',
                     'revision_timestamp',
                     'user_type',
                     'user_username',
                     'user_id',
                     'revision_minor',
                     'bytes'
                     ]


csv_output_fields_with_change = csv_output_fields + ['change_bytes']


Revision = NamedTuple('Revision', [
    ('id', int),
    ('parent_id', int),
    ('user', Optional[mwxml.Revision.User]),
    ('minor', bool),
    ('comment', str),
    ('nbytes', int),
    ('model', str),
    ('format', str),
    ('timestamp', jsonable.Type),
])


Page = NamedTuple('Page', [
    ('id', str),
    ('namespace', int),
    ('title', str),
    ('revisions', Iterable[Revision]),
])


def extract_revisions(
        mw_page: mwxml.Page,
        language: str,
        stats: Mapping,
        only_last_revision: bool) -> Iterator[Revision]:
    """Extract basic info from the revisions."""

    revisions = more_itertools.peekable(mw_page)
    for mw_revision in revisions:
        utils.dot()

        is_last_revision = not utils.has_next(revisions)
        if only_last_revision and not is_last_revision:
            continue

        nbytes = -1
        try:
            if mw_revision.text:
                nbytes = len(mw_revision.text.encode('utf-8'))
            else:
                nbytes = 0
        except:
            import ipdb; ipdb.set_trace()

        yield Revision(
            id=mw_revision.id,
            parent_id=mw_revision.parent_id,
            user=mw_revision.user,
            minor=mw_revision.minor,
            nbytes=nbytes,
            comment=mw_revision.comment,
            model=mw_revision.model,
            format=mw_revision.format,
            timestamp=mw_revision.timestamp.to_json()
        )
        stats['performance']['revisions_analyzed'] += 1


def extract_pages(
        dump: Iterable[mwxml.Page],
        language: str,
        stats: Mapping,
        only_last_revision: bool) -> Iterator[Page]:
    """Extract revisions from a page."""
    for mw_page in dump:
        utils.log("Processing", mw_page.title)

        # Skip non-articles
        if mw_page.namespace != 0:
            utils.log('Skipped (namespace != 0)')
            continue

        revisions_generator = extract_revisions(
            mw_page,
            language=language,
            stats=stats,
            only_last_revision=only_last_revision,
        )

        yield Page(
            id=mw_page.id,
            namespace=mw_page.namespace,
            title=mw_page.title,
            revisions=revisions_generator,
        )
        stats['performance']['pages_analyzed'] += 1


def configure_subparsers(subparsers):
    """Configure a new subparser."""
    parser = subparsers.add_parser(
        'extract-revisionlist',
        help='Extract basic info about revisions.',
    )
    parser.add_argument(
        '-l', '--language',
        choices=languages.supported,
        required=True,
        help='The language of the dump.',
    )
    parser.add_argument(
        '--only-last-revision',
        action='store_true',
        help='Consider only the last revision for each page.',
    )
    parser.add_argument(
        '-s', '--ensure-sorted',
        action='store_true',
        help='Ensure that the revisions are sorted by time for each page.',
    )
    parser.add_argument(
        '-c', '--change-bytes',
        action='store_true',
        help='Calculate the difference in bytes between each revision '
             '(implies --ensure-sorted)',
    )
    parser.set_defaults(func=main)


def main(
        dump: Iterable[mwxml.Page],
        features_output_h,
        stats_output_h,
        args) -> None:
    """Main function that parses the arguments and writes the output."""
    stats = {
        'performance': {
            'start_time': None,
            'end_time': None,
            'revisions_analyzed': 0,
            'pages_analyzed': 0,
        },
    }
    stats['performance']['start_time'] = datetime.datetime.utcnow()

    writer = csv.writer(features_output_h)

    pages_generator = extract_pages(
        dump,
        language=args.language,
        stats=stats,
        only_last_revision=args.only_last_revision,
    )

    # --change-bytes implies --ensure-sorted
    if args.change_bytes:
        args.ensure_sorted = True

    # write output header
    if args.change_bytes:
        writer.writerow(csv_output_fields_with_change)
    else:
        writer.writerow(csv_output_fields)

    for mw_page in pages_generator:
        page_revision_list = []

        for revision in mw_page.revisions:

            if revision.user is None:
                user_type = 'None'
                user_username = 'None'
                user_id = -2
            else:
                if revision.user.id is not None:
                    user_type = 'registered'
                    user_username = revision.user.text
                    user_id = revision.user.id
                else:
                    user_type = 'ip'
                    user_username = revision.user.text
                    user_id = -1

            revision_parent_id = revision.parent_id
            if revision.parent_id is None:
                revision_parent_id = -1

            if revision.minor:
                revision_minor = 1
            else:
                revision_minor = 0

            revout = [mw_page.id,
                      mw_page.title,
                      revision.id,
                      revision.parent_id,
                      revision.timestamp,
                      user_type,
                      user_username,
                      user_id,
                      revision_minor,
                      revision.nbytes
                      ]

            # change_bytes is redundant with respect to ensure_sorted, but we
            # repeat it here for clarity
            if args.ensure_sorted or args.change_bytes:
                page_revision_list.append(revout)
            else:
                writer.writerow(revout)

        if page_revision_list:

            # revout:
            #   - 0: mw_page.id,
            #   - 1: mw_page.title,
            #   - 2: revision.id,
            #   - 3: revision.parent_id,
            #   - 4: revision.timestamp,
            #   - 5: user_type,
            #   - 6: user_username,
            #   - 7: user_id,
            #   - 8: revision_minor,
            #   - 9: bytes
            page_revision_list.sort(key=lambda revout: arrow.get(revout[4]))
            prev_nbites = None
            for revout in page_revision_list:
                if args.change_bytes:
                    nbytes = revout[9]
                    if prev_nbites is None:
                        change = nbytes
                    else:
                        change = nbytes - prev_nbites

                    writer.writerow(revout + [change])
                    prev_nbites = nbytes
                else:
                    writer.writerow(revout)

    stats['performance']['end_time'] = datetime.datetime.utcnow()

    with stats_output_h:
        dumper.render_template(
            stats_template,
            stats_output_h,
            stats=stats,
        )
