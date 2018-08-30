"""Extract redirects from pages.

The output format is csv.
"""

import csv
import collections
import datetime
import functools

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


Revision = NamedTuple('Revision', [
    ('id', int),
    ('parent_id', int),
    ('user', Optional[mwxml.Revision.User]),
    ('minor', bool),
    ('comment', str),
    ('model', str),
    ('format', str),
    ('timestamp', jsonable.Type),
    ('text', str),
    ('redirects', Iterable[extractors.redirect.Redirect])
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
        stats: Mapping) -> Iterator[Revision]:
    """Extract the internall links (wikilinks) from the revisions."""

    revisions = more_itertools.peekable(mw_page)
    for mw_revision in revisions:
        utils.dot()

        text = utils.remove_comments(mw_revision.text or '')

        redirects = (redirect
                     for redirect, _
                     in extractors.redirect.redirects(text, language=language))

        yield Revision(
            id=mw_revision.id,
            parent_id=mw_revision.parent_id,
            user=mw_revision.user,
            minor=mw_revision.minor,
            comment=mw_revision.comment,
            model=mw_revision.model,
            format=mw_revision.format,
            timestamp=mw_revision.timestamp.to_json(),
            text=text,
            redirects=redirects
        )
        stats['performance']['revisions_analyzed'] += 1


def extract_pages(
        dump: Iterable[mwxml.Page],
        language: str,
        stats: Mapping) -> Iterator[Page]:
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
            stats=stats
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
        'extract-redirects',
        help='Extract redirects.',
    )
    parser.add_argument(
        '-l', '--language',
        choices=languages.supported,
        required=True,
        help='The language of the dump.',
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
    )

    writer.writerow((
        'page_id',
        'page_title',
        'revision_id',
        'revision_parent_id',
        'revision_timestamp'
        'revision_minor',
        'redirect.target',
        'redirect.tosection'
        ))

    for mw_page in pages_generator:
        hasredirect_rev = None
        hasredirect_prevrev = None

        for revision in sorted(mw_page.revisions, key=lambda r: r.timestamp):

            revision_parent_id = revision.parent_id
            if revision.parent_id is None:
                revision_parent_id = -1

            if revision.minor:
                revision_minor = 1
            else:
                revision_minor = 0

            redirect_list = [red for red in revision.redirects]
            if len(redirect_list) > 0:
                # there is a redirect in this revision
                for redirect in redirect_list:
                    hasredirect_rev = True

                    redirect_target = redirect.target
                    redirect_tosection = redirect.tosection
                    # project,page.id,page.title,revision.id,revision.parent_id,
                    # revision.timestamp,contributor_if_exists(revision.user),
                    # revision.minor,wikilink.link,wikilink.anchor,
                    # wikilink.section_name,wikilink.section_level,
                    # wikilink.section_number
                    writer.writerow((
                        mw_page.id,
                        mw_page.title,
                        revision.id,
                        revision.parent_id,
                        revision.timestamp,
                        revision_minor,
                        redirect_target,
                        redirect_tosection
                    ))
            else:
                # no redirect in this revision
                hasredirect_rev = False
                if hasredirect_prevrev:

                    redirect_target = '#NOREDIRECT'
                    redirect_tosection = ''
                    writer.writerow((
                        mw_page.id,
                        mw_page.title,
                        revision.id,
                        revision.parent_id,
                        revision.timestamp,
                        revision_minor,
                        redirect_target,
                        redirect_tosection
                    ))

            hasredirect_prevrev = hasredirect_rev

    stats['performance']['end_time'] = datetime.datetime.utcnow()

    with stats_output_h:
        dumper.render_template(
            stats_template,
            stats_output_h,
            stats=stats,
        )
