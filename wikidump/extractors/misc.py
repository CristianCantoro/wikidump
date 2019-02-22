"""Various extractors."""
import functools

import regex
import signal
import itertools
from more_itertools import peekable
from typing import (Callable, Iterable, Iterator, List, TypeVar, NamedTuple,
                    Optional)

from . import arxiv, doi, isbn, pubmed
from .common import CaptureResult, Span
from .. import timeout

# empty generator
# Python Empty Generator Function
# https://stackoverflow.com/a/13243870/2377454
def empty_generator():
    yield from ()


class Section:
    """Section class."""
    def __init__(self, name: str, level: int, body: str):
        """Instantiate a section."""
        self.name = name
        self.level = level
        self.body = body
        self._full_body = None

    @property
    def is_preamble(self):
        """Return True when this section is the preamble of the page."""
        return self.level == 0

    @property
    def full_body(self) -> str:
        """Get the full body of the section."""
        if self._full_body is not None:
            return self._full_body

        if self.is_preamble:
            full_body = self.body
        else:
            equals = ''.join('=' for _ in range(self.level))
            full_body = '{equals}{name}{equals}\n{body}'.format(
                equals=equals,
                name=self.name,
                body=self.body,
            )
        self._full_body = full_body
        return full_body

    def __repr__(self):
        'Return a nicely formatted representation string'
        template = '{class_name}(name={name!r}, level={level!r}, '\
            'body={body!r})'
        return template.format(
            class_name=self.__class__.__name__,
            name=self.name,
            level=self.level,
            body=self.body[:20],
        )


section_header_re = regex.compile(
    r'''^
        (?P<equals>=+)              # Match the equals, greedy
        (?P<section_name>           # <section_name>:
            .+?                     # Text inside, non-greedy
        )
        (?P=equals)\s*              # Re-match the equals
        $
    ''', regex.VERBOSE | regex.MULTILINE)

templates_re = regex.compile(
    r'''
        \{\{
        (?P<content>(?s).*?)
        \}\}
    ''', regex.VERBOSE)


@functools.lru_cache(maxsize=1000)
def _pattern_or(words: List) -> str:
    words_joined = '|'.join(words)

    return r'(?:{})'.format(words_joined)


def references(source: str) -> Iterator[CaptureResult[str]]:
    """Return all the references found in the document."""
    pattern = regex.compile(
        r'''
            <ref
            .*?
            <\/ref>
        ''', regex.VERBOSE | regex.IGNORECASE | regex.DOTALL)

    for match in pattern.finditer(source):
        yield CaptureResult(match.group(0), Span(*match.span()))


def sections(source: str, include_preamble: bool=False) \
        -> Iterator[CaptureResult[Section]]:
    """Return the sections found in the document."""
    section_header_matches = peekable(section_header_re.finditer(source))
    if include_preamble:
        try:
            body_end = section_header_matches.peek().start()
            body_end -= 1  # Don't include the newline before the next section
        except StopIteration:
            body_end = len(source)
        preamble = Section(
            name='',
            level=0,
            body=source[:body_end],
        )
        yield CaptureResult(preamble, Span(0, body_end))

    for match in section_header_matches:
        name = match.group('section_name')
        level = len(match.group('equals'))

        body_begin = match.end() + 1  # Don't include the newline after
        try:
            body_end = section_header_matches.peek().start()
            body_end -= 1  # Don't include the newline before the next section
        except StopIteration:
            body_end = len(source)

        section = Section(
            name=name,
            level=level,
            body=source[body_begin:body_end],
        )

        yield CaptureResult(section, Span(match.start(), body_end))


# @functools.lru_cache(maxsize=10)
# @utils.listify
# def citations(source, language):
#     citation_synonyms = languages.citation[language]

#     citation_synonyms_pattern = _pattern_or(citation_synonyms)

#     pattern = regex.compile(
#         r'''
#             \{\{
#             \s*
#             %s
#             \s+
#             (?:(?s).*?)
#             \}\}
#         ''' % (citation_synonyms_pattern,), regex.VERBOSE
#     )

#     for match in pattern.finditer(source):
#         yield match.group(0)


def templates(source: str) -> Iterator[CaptureResult[str]]:
    """Return all the templates found in the document."""
    for match in templates_re.finditer(source):
        yield CaptureResult(match.group(0), Span(*match.span()))


T = TypeVar('T')
Extractor = Callable[[str], T]


def pub_identifiers(source: str, extractors: Iterable[Extractor]=None) -> T:
    """Return all the identifiers found in the document."""
    if extractors is None:
        extractors = (
            arxiv.extract,
            doi.extract,
            isbn.extract,
            pubmed.extract,
        )
    for identifier_extractor in extractors:
        for capture in identifier_extractor(source):
            yield capture


class Wikilink:
    """Link class."""
    def __init__(self,
                 link: str,
                 tosection: str,
                 anchor: str,
                 section_name: str,
                 section_level: int,
                 section_number: int):
        """Instantiate a link."""
        self.link = link
        self.tosection = tosection
        self.anchor = anchor
        self.section_name = section_name
        self.section_level = section_level
        self.section_number = section_number

    def __repr__(self):
        'Return a nicely formatted representation string'
        template = '{class_name}(link={link!r}, anchor={anchor!r})'
        return template.format(
            class_name=self.__class__.__name__,
            link=self.link,
            anchor=self.anchor,
        )

# See https://regex101.com/r/kF0yC9/14
#
# The group 'total' matches everything that is around the link, delimited by
# spaces, this is because the actual anchor text can be built prepending or
# appending text to the actual wikilink. So [[apple]]s will point to the page
# 'Apple', but it will be visualized as 'apples', including the "s".
#
# The group 'wikilink' matches the whole wikilink, including square brackets.
#
# The text inside the 'link' group is title of the page, it is limited to 256
# chars since it is the max supported by MediaWiki for page titles [1].
# Furthermore:
#   * pipes and brackets (|,[,]) are invalid characters for page
#     titles [2];
#   * newlines are not allowed [3]
#   * the pound sign (#) is not allowed in page titles, but links can point
#     to sections and we want to capture that.
# The anchor text allows pipes and closed brackets, but not open ones [3],
# newlines are allowed [3].
# See:
# [1] https://en.wikipedia.org/w/index.php?title=Wikipedia:Wikipedia_records\
#    &oldid=709472636#Article_with_longest_title
# [2] https://www.mediawiki.org/w/index.php?title=Manual:$wgLegalTitleChars\
#    &oldid=1274292
# [3] https://it.wikipedia.org/w/index.php?\
#   title=Utente:CristianCantoro/Sandbox&oldid=79784393#Test_regexp
REGEX_TIMEOUT = 5


wikilink_re = regex.compile(
    r'''\s?                                 # Match optional space
        (?P<total>                          # named group <total>:
        \S*?                                # Match any non-space non-greedily
          (?P<wikilink>                     # <wikilink>:
                                            # Match the whole wikilink
                                            # - including brackets
            \[\[                            # Match two opening brackets
            (?P<link>                       # <link>:
               [^\n\|\]\[\<\>\{\}]{0,256}   # Text inside link group
                                            # everything not illegal in page
                                            # title except pound-sign,
                                            # non-greedy
                                            # can be empty or up to 256 chars
            )
            (?:                             # Non-capturing group
               \|                           # Match a pipe
               (?P<anchor>                  # <anchor>:
                   [^\[]*?                  # Test inside anchor group:
                                            # match everything not an open
                                            # bracket - non greedily
                                            # if empty the anchor text is link
              )
            )?                              # anchor text is optional
            \]\]                            # Match two closing brackets
          )                                 # Close wikilink group
        \S*)                                # Any additional non-space
        \s?                                 # Match optional space
     ''', regex.VERBOSE | regex.MULTILINE)


wikilink_simple_re = regex.compile(
    r'''\[\[                # Match two opening brackets
         [^\n\]\[]+?
        \]\]                # Match two closing brackets
     ''', regex.VERBOSE | regex.MULTILINE)


space_re = regex.compile(r'\s')

# the regex module supports reverse search
# https://pypi.org/project/regex/
space_rtl_re = regex.compile(r"(?r)\s")


SectionLimits = NamedTuple('SectionLimits', [
    ('name', str),
    ('level', int),
    ('number', int),
    ('begin', int),
    ('end', bool)
])


def reverse_position(revpos: int, strlen: int) -> int:
    if revpos == -1:
        return -1

    # the modulus of a negative number is positive, also this number goes
    # from 0 to strlen-1 (same as the valid indexes of a string).
    #
    # This is the logic:
    #    original vector          reversed vector
    #   |0 |1 |2 |3 |4 |5 |      |0 |1 |2 |3 |4 |5 |
    #   |->|->|->|* |# |->|  =>  |<-|# |* |<-|<-|<-|
    #
    #   -(revpos+1)              |-1|-2|-3|-4|-5|-6|
    #   -(revpos+1) % strlen     |5 |4 |3 |2 |1 |0 |
    #
    # revpos = 1  =>  pos = 4
    return -(revpos+1) % strlen


def wikilinks(page_title: str,
              source: str,
              sections: Iterator[CaptureResult[Section]],
              debug: Optional[bool]=False) \
        -> Iterator[CaptureResult[Wikilink]]:
    """Return the wikilinks found in the document."""

    wikilink_simple_matches = empty_generator()

    # We could try to find instances of parenthesys, but we try first to
    # just find whole links with the simple regex. After all, many pages will
    # have links and this check is not going to be very helpful.
    # if source.find('[[') is not -1 \
    #         and source.find(']]') is not -1:
    #     # equivalent to
    #     #  if '[[' in line and ']]' in line
    #     # but way more efficient
    #     # https://www.agnosticdev.com/content/
    #     #   how-find-substring-string-python
    #     wikilink_simple_matches = peekable(
    #         wikilink_simple_re.finditer(source,concurrent=True))
    # else:
    #     return
    if debug:
        try:
            wikilink_simple_matches = timeout.wrap_timeout(
                lambda t: peekable(wikilink_simple_re.finditer(t,concurrent=True)),
                REGEX_TIMEOUT,
                [source]
                )
        except CallTimeout as exception:
            import ipdb; ipdb.set_trace()

    else:
        wikilink_simple_matches = peekable(
            wikilink_simple_re.finditer(source,concurrent=True)
            )

    sections_limits = [SectionLimits(name=section.name,
                                     level=section.level,
                                     number=idx,
                                     begin=span.begin,
                                     end=span.end)
                       for idx, (section, span) in enumerate(sections, 1)]

    last_section_seen = 0
    prevmatch_start = 0
    prevmatch_end = 0
    for simple_match in wikilink_simple_matches:

        # we actually want the last occurrence of a space before a parenthesys
        # so we reverse the string and we search for the first occurrence.
        # revtext = source[prevmatch_start:simple_match.start()][::-1]
        space_prev_match = space_rtl_re.search(
            source[prevmatch_start:simple_match.start()]
            )
        if space_prev_match:
            spacepos = space_prev_match.start()
            space_prev_match_pos = reverse_position(spacepos, len(revtext))

            space_prev_pos = prevmatch_start + space_prev_match.start()
        else:
            space_prev_pos = simple_match.start()
        del revtext

        space_post_match = space_re.search(
            source[simple_match.end():]
            )
        if space_post_match:
            space_post_pos = simple_match.end() + space_post_match.start()
        else:
            # end of text
            space_post_pos = simple_match.end()

        match = None
        subtext = source[space_prev_pos:space_post_pos]
        if debug:
            try:
                match = timeout.wrap_timeout(
                    wikilink_re.search,
                    REGEX_TIMEOUT,
                    [subtext]
                    )
            except CallTimeout as exception:
                import ipdb; ipdb.set_trace()
        else:
            match = wikilink_re.search(subtext)

        if match is None:
            simple_match_text = (simple_match.group(0)
                                 .strip()
                                 .lstrip('[')
                                 .rstrip(']')
                                 )

            # wikilink_re is not matching because of illegal characters in
            # the link:
            if simple_match_text.find('|') or \
                    simple_match_text.find('>') or \
                    simple_match_text.find('<') or \
                    simple_match_text.find('{') or \
                    simple_match_text.find('}'):
                continue
            else:
                import ipdb; ipdb.set_trace()

        else:
            prevmatch_start = match.start()
            prevmatch_end = match.end()

            link = match.group('link') or ''
            link = link.strip()

            # split on '#' (link to section)
            tosection = ''
            if '#' in link:
                splitlink = link.split('#', 1)
                link = splitlink[0]
                if not link:
                    link = page_title
                tosection = splitlink[1]

            anchor = match.group('anchor') or link

            # newlines in anchor are visualized as spaces.
            anchor = anchor.replace('\n', ' ')
            anchor = ' '.join(anchor.strip().split())

            total_start = match.start('total')
            total_end = match.end('total')

            link_section_number = 0
            link_section_name = '---~--- incipit ---~---'
            link_section_level = 0

            for section in sections_limits[last_section_seen:]:
                if section.begin <= total_start <= section.end:
                    link_section_number = section.number
                    link_section_name = section.name
                    link_section_level = section.level
                    last_section_seen = (link_section_number - 1)\
                        if link_section_number > 0 else 0
                    break

            # There are cases in which in the wikitext you will find cases
            # such as:
            #   - [[ |yoda]]
            #   - [[|diety|god]]
            #   - [[]]
            # Note: * the first case never occours, because the (software)
            #       editor would auto-correct it in [[yoda]], it may be
            #       something that could occour in a past version of the
            #       software.
            #       * in the last case both 'link' and 'anchor' are empty)
            #
            # We consider these cases to be broken no matter what and we
            # ignore them
            if not link:
                continue

            wikilink = Wikilink(
                link=link,
                anchor=anchor,
                tosection=tosection,
                section_name=link_section_name,
                section_level=link_section_level,
                section_number=link_section_number
            )

            anchor_prefix = (source[match.start('total'):match.start('wikilink')]
                             .strip('[')
                             )
            anchor_suffix = (source[match.end('wikilink'):match.end('total')]
                             .strip(']')
                             )
            anchor = anchor_prefix + anchor + anchor_suffix

            # print(source[total_start:total_end])
            yield CaptureResult(wikilink, Span(total_start, total_end))

    return
