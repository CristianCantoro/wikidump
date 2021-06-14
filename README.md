# wikidump

Framework for the extraction of features from Wikipedia XML dumps.

## Installation

This project has been tested with Python >= 3.5, but we are targeting the
newest releases of Python 3, so we don't promise backwards compatibility
with earlier versions. In particular, we recomend to use Python >= 3.6.

If you find some bug on that front, open an [issue][issue].

You need to install dependencies first, as usual.

```bash
pip3 install -r requirements.txt
```

## How it Works

You need to download Wikipedia dumps first, see the `download.sh` script. If
you want a more complete set of scripts check out the [wikidump-download-tools][wdt]

The module needs to be executed with `python3 -m`, which basically runs the
file `__main__.py` inside the module.

The module is structured in subcommands that run processors that accomplish
a given task:

```bash
python3 -m wikidump FILE [FILE ...] {subcommand}
```

It will take some time, all extractors have been written trying to minimize
RAM comsumption.

### Usage

```plain
$ python3 -m wikidump -h
usage: wikidump [-h] [--output-dir OUTPUT_DIR] [--output-compression {7z,gzip,None,bz2}] [--dry-run]
                [FILE [FILE ...]] {extract-bibliography,extract-identifiers,extract-identifiers-history,extract-page-ids,extract-redirects,extract-revisionlist,count-sections,extract-wikilinks} ...

Wikidump features extractor.

positional arguments:
  FILE                  XML Wikidump file to parse. It accepts 7z or bzip2.
  {extract-bibliography,extract-identifiers,extract-identifiers-history,extract-page-ids,extract-redirects,extract-revisionlist,count-sections,extract-wikilinks}
                        sub-commands help
    extract-bibliography
                        Extract only sections may be a bibliography
    extract-identifiers
                        Extract the identifiers from the text (doi, isbn, arxiv and pubmed).
    extract-identifiers-history
                        Extract the identifiers from the text (doi, isbn, arxiv and pubmed).
    extract-page-ids    Extract the page ids from the text.
    extract-redirects   Extract redirects.
    extract-revisionlist
                        Extract basic info about revisions.
    count-sections      Count the number of sections and the section names of the dump.
    extract-wikilinks   Extract internal links (wikilinks)

optional arguments:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR
                        Output directory for processed results [default: ./output].
  --output-compression {7z,gzip,None,bz2}
                        Output compression format [default: None].
  --dry-run, -n         Don't write any file
```

Each subcommand has its own help message, watch out for required arguments:

```plain
$ python3 -m wikidump extract-bibliography -h
usage: wikidump [FILE [FILE ...]] extract-bibliography [-h] -l {de,sv,fr,ru,nl,en,it,es,pl} [--only-last-revision]

optional arguments:
  -h, --help            show this help message and exit
  -l {de,sv,fr,ru,nl,en,it,es,pl}, --language {de,sv,fr,ru,nl,en,it,es,pl}
                        The language of the dump.
  --only-last-revision  Consider only the last revision for each page.
```

## How to Cite

If you use this library, please cite this paper that, among other things,
describes its usage to extract links from Wikipedia.

```plain
Consonni, Cristian, David Laniado, and Alberto Montresor.
"WikiLinkGraphs: A complete, longitudinal and multi-language dataset of the Wikipedia link networks."
Proceedings of the International AAAI Conference on Web and Social Media. Vol. 13. 2019.
```

```bibtex
@inproceedings{consonni2019wikilinkgraphs,
  title={WikiLinkGraphs: A complete, longitudinal and multi-language dataset of the Wikipedia link networks},
  author={Consonni, Cristian and Laniado, David and Montresor, Alberto},
  booktitle={Proceedings of the International AAAI Conference on Web and Social Media},
  volume={13},
  pages={598--607},
  year={2019}
}
```

## Authors

This library was initiated by [Alessio Bogon][youtux] in 2015 and expanded by
[Cristian Consonni][CristianCantoro].

[issue]: https://github.com/WikiLinkGraphs/wikidump/issues
[wdt]: https://github.com/CristianCantoro/wikidump-download-tools
[youtux]: https://github.com/youtux
[CristianCantoro]: https://github.com/CristianCantoro
[wikilink]: https://ojs.aaai.org/index.php/ICWSM/article/download/3257/3125
[wdt]: https://github.com/CristianCantoro/wikidump-download-tools