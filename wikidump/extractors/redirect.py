"""Redirect extractors."""

import regex
from more_itertools import peekable
from typing import Iterable, Iterator

from .common import CaptureResult, Span

# Synonims for #REDIRECT for the various languages
# (h/t to Reedy from #mediawiki on freebode)
redirect_magicwords = {
  # https://github.com/wikimedia/mediawiki/blob/master/languages/messages/MessagesDe.php#L154
  'de': ['WEITERLEITUNG', 'REDIRECT'],
  # https://github.com/wikimedia/mediawiki/blob/master/languages/messages/MessagesEn.php#L215
  'en': ['REDIRECT'],
  # https://github.com/wikimedia/mediawiki/blob/master/languages/messages/MessagesEs.php#L151
  'es': ['REDIRECCIÓN', 'REDIRECCION', 'REDIRECT'],
  # https://github.com/wikimedia/mediawiki/blob/master/languages/messages/MessagesFr.php#L144
  'fr': ['REDIRECTION', 'REDIRECT'],
  # https://github.com/wikimedia/mediawiki/blob/master/languages/messages/MessagesIt.php#L158
  'it': ['RINVIA', 'RINVIO', 'RIMANDO', 'REDIRECT'],
  # https://github.com/wikimedia/mediawiki/blob/master/languages/messages/MessagesNl.php#L115
  'nl': ['DOORVERWIJZING', 'REDIRECT'],
  # https://github.com/wikimedia/mediawiki/blob/master/languages/messages/MessagesPl.php#L236
  'pl': ['PATRZ', 'PRZEKIERUJ', 'TAM', 'REDIRECT'],
  # https://github.com/wikimedia/mediawiki/blob/master/languages/messages/MessagesRu.php#L237
  'ru': ['перенаправление', 'перенапр', 'REDIRECT'],
  # https://github.com/wikimedia/mediawiki/blob/master/languages/messages/MessagesSv.php#L201
  'sv': ['OMDIRIGERING', 'REDIRECT'],
}


class Redirect:
    """Redirect class."""
    def __init__(self,
                 target: str,
                 tosection: str):
        """Instantiate a link."""
        self.target = target
        self.tosection = tosection

    def __repr__(self):
        'Return a nicely formatted representation string'
        template = '{class_name}(target={target!r})'
        return template.format(
            class_name=self.__class__.__name__,
            target=self.target,
        )


# See https://regex101.com/r/YWSvyd/2
# See the previous comment on wikilink_re about valid page titles.

redirect_base_pattern = \
r'''\A                                # Match the beginning of the text
    \s*                               # Match optional spaces
    \#REDIRECT                        # Match the exact string REDIRECT
    \s*                               # Match optional spaces
    \[\[                              # Match two opening brackets
   (?P<link>                          # <link>:
       [^\n\|\]\[\<\>\{\}]{0,256}     # Text inside link group
                                      # everything not illegal, non-greedy
                                      # can be empty or up to 256 chars
   )
   (?:                                # Non-capturing group
      \|                              # Match a pipe
      (?P<anchor>                     # Match an anchor without naming the group:
          [^\[]*?                     # Test inside anchor group:
                                      # match everything not an open braket
                                      # - non greedy
                                      # if empty the anchor text is link
      )
   )?                                 # anchor text is optional
   \]\]                               # Match two closing brackets
 '''


redirect_res = dict()
for lang, word_list in redirect_magicwords.items():

  # if it is just one word take it, otherwise make a list of options for
  # the regex, i.e:
  #   en -> REDIRECT
  #   it -> (RINVIA|RINVIO|RIMANDO|REDIRECT)
  redirect_alt = word_list[0]
  if len(word_list) > 1:
    redirect_alt = '({})'.format('|'.join(word_list))

  redirect_pattern = redirect_base_pattern.replace('REDIRECT',
                                                   redirect_alt,
                                                   1
                                                   )
  redirect_res[lang] = regex.compile(
      redirect_pattern, (regex.VERBOSE|regex.MULTILINE|regex.IGNORECASE))


def redirects(source: str, language: str) -> Iterator[CaptureResult[Redirect]]:
    """Return the wikilinks found in the document."""

    redirect_re = redirect_res[language]
    redirect_matches = peekable(redirect_re.finditer(source, concurrent=True))

    for match in redirect_matches:
        target = match.group('link') or ''
        target = target.strip()
        anchor = match.group('anchor') or target
        # newlines in anchor are visualized as spaces.
        anchor = anchor.replace('\n', ' ').strip()

        # split on '#' (link to section)
        tosection = ''
        if '#' in target:
            splittarget = target.split('#', 1)
            target = splittarget[0]
            tosection = splittarget[1]

        # For some reason if wikilink has no pipe, e.g. [[apple]] the regex
        # above captures everything in the anchor group, so we need to set
        # the link to the same page.
        if (anchor and not target):
            target = anchor

        redirect = Redirect(
            target=target,
            tosection=tosection
        )

        yield CaptureResult(redirect, Span(match.start(), match.end()))
