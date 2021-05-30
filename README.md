# wikidump

Framework for the extraction of features from Wikipedia XML dumps.

## Installation

This project has been tested with Python >=3.5.0, but we are targeting the
newest releases of Python 3, so we don't promise backwards compatibility
with earlier versions. If you find some bug on that front, open an
[issue][issue].

You need to install dependencies first, as usual.

```bash
pip3 install -r requirements.txt
```

## Usage

You need to download Wikipiedia dumps first:

```bash
./download.sh
```

if you want a more complete set of scripts check out the
[wikidump-download-tools][wdt] repo.

Then run the extractor:

```bash
python -m wikidump FILE [FILE ...] OUTPUT_DIR
```

It will take some time, all extractors have been written trying to minimize
RAM comsumption.

## Authors

This library was initiated by [Alessio Bogon][youtux] in 2015 and expanded by
[Cristian Consonni][CristianCantoro].

[issue]: https://github.com/WikiLinkGraphs/wikidump/issues
[wdt]: https://github.com/CristianCantoro/wikidump-download-tools
[youtux]: https://github.com/youtux
[CristianCantoro]: https://github.com/CristianCantoro
