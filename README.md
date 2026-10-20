# ph-power-rates test

A small, honest test of one question: can the rate publications of Philippine distribution utilities (PDFs, web pages, Facebook posts) be turned into one table of `utility, month, price per kWh, generation charge` by code, with every number traceable to its source line?

Ten publications from eight utilities, three formats, run on 2026-10-20. Result and findings in `report.md`. The table is in `out/rates.csv`; every row carries the source URL, the fetch time and the text clip the number came from.

## Run it

```
python3 scripts/collect.py          # fetches the ten live sources, writes out/rates.csv and out/rates.json, saves raw files under sources/
python3 scripts/second_reader.py    # optional: an independent model read of the same saved text, for comparison
```

Requirements: Python 3, `pdftotext` (poppler). The second reader uses a small model through a local routing script and is not needed for the table.

## Schema

| column | meaning |
|---|---|
| utility | the distribution utility or electric cooperative, as it names itself |
| month | the billing month the publication is for, as written in the source |
| residential_rate_php_per_kwh | the residential rate per kWh the source states, or `not in source` |
| rate_basis | what that number is in the source's own terms (overall rate, total energy charges before VAT, ...) |
| generation_charge_php_per_kwh | the generation charge or generation rate per kWh the source states as a level, or `not in source` |
| generation_basis | what that number is in the source's own terms |
| source_url, fetched_at_utc, format | provenance |
| status | `parsed`, `parse failed`, `no rate field in source`, `unreachable` |
| evidence | the text clips the month and numbers were read from |

Rules: a number is copied as printed, never computed or rounded. A field the source does not state is `not in source`, not a guess. A page that needs a login is `unreachable`. Different bases are kept apart; nothing here is a like for like comparison between utilities until a reviewer says the bases match.

Context: written as the prototype for an application to the BetterGovPH Fellowship 2026, Energy track (deck ask 2, "one price table"). Sources are the utilities' own public pages; no scraping behind a login, no personal data.
