# Prototype test: ten utility rate publications into one price table
BetterGov Fellowship 2026, Energy track. Run on 2026-10-20, 10:04 to 10:50 UTC, by the build lane on Aaron's "run test" (#therapy). Planned for 2026-10-27 in the sketch; run a week early. Nothing here was sent or submitted anywhere.

## What was tested
The deck's ask 2: "The 142 utilities publish their rates as PDFs, web tables, and Facebook posts. Write the scrapers and schema that turn those into one dataset: utility, month, price per kWh, generation charge."
Ten publications, three formats, from the utilities' own sites, fetched live by `scripts/collect.py`:

| # | Utility | Format | Publication | Month |
|---|---|---|---|---|
| 1 | Meralco | web advisory | "Higher Residential Rates this October 2026" | October 2026 |
| 2 | Meralco | PDF | Breakdown of Generation Charge, October 2026 | October 2026 |
| 3 | ILECO III (Iloilo) | PDF | Advisory on Unbundled Rates, October 2026 billing month | October 2026 |
| 4 | MORE Power (Iloilo City) | PDF | Breakdown of Generation Charge, billing cycle October 2026 | October 2026 |
| 5 | Angeles Electric | PDF | Breakdown of Generation Charge, Annex A, October 2026 | October 2026 |
| 6 | BENECO (Benguet) | web table | rates.php, "Current Rates at a Glance" | September 2026 |
| 7 | Davao Light | web advisory | "Higher Generation Charge Drives July 2026 Electricity Rate" | July 2026 |
| 8 | Visayan Electric (Cebu) | web advisory | "limiting August rate adjustment to P0.06/kWh" | August 2026 |
| 9 | BENECO (Benguet) | Facebook page | facebook.com/benguetelectric | |
| 10 | SOLECO (Southern Leyte) | Facebook page | facebook.com/SOLECOInc | |

Schema written per row (`out/rates.csv`): utility, month, residential_rate_php_per_kwh, rate_basis, generation_charge_php_per_kwh, generation_basis, source_url, fetched_at_utc, format, status, evidence (the text clip the number came from).

## Result
| Format | Sources | Reachable | Fields the source states | Parsed correctly | Wrong | Not stated, correctly marked |
|---|---|---|---|---|---|---|
| PDF | 4 | 4 | 9 (4 months, 1 rate, 4 generation charges) | 9 | 0 | 3 (no total residential rate in a generation charge breakdown) |
| web | 4 | 4 | 8 (4 months, 4 rates) | 8 | 0 | 4 (advisories give the change in the generation charge, never its level) |
| Facebook | 2 | 0 | 0 | 0 | 0 | both pages redirect to a login screen from a server |
| total | 10 | 8 | 17 | 17 | 0 | 7 |

The numbers, all checked by eye against the clip in the evidence column (clips in `out/rates.csv` and `out/rates.json`):

| Utility | Month | Residential rate, PhP/kWh | Generation charge, PhP/kWh |
|---|---|---|---|
| Meralco | October 2026 | 15.0615 (overall rate, typical household) | not in the advisory |
| Meralco | October 2026 | not in the table | 10.2005 (average generation charge) |
| ILECO III | October 2026 | 9.6759 (total energy charges, residential, VAT exclusive) | 7.6432 (generation energy charge, residential) |
| MORE Power | October 2026 | not in the table | 7.6318 (total generation rate, VAT exclusive) |
| Angeles Electric | October 2026 | not in the table | 7.2549 (blended generation rate) |
| BENECO | September 2026 | 11.80 | not on the rates page |
| Davao Light | July 2026 | 13.09 | not in the advisory |
| Visayan Electric | August 2026 | 14.96 | not in the advisory |

## Second reader
An independent read by deepseek flash (`scripts/second_reader.py`, the same fields from the same saved text, without the collector's answer) agreed on 7 of 8 reachable sources, field for field, including every "not in source". The one disagreement: on the ILECO III unbundled rate sheet the reader returned "not in source" for both numbers. The sheet does carry both lines ("Generation Energy Charge PhP/kWh 7.6432" and "TOTAL ENERGY CHARGES PhP/kWh 9.6759"), so the collector stands, with the caveat already in the basis column: an unbundled rate sheet has no single "effective residential rate" line, and the total shown is before VAT. This is the kind of row the analyst's review queue exists for.

## What the test says about the real build
1. **The three formats behave differently.** PDFs from the utilities carry the generation charge level and are clean to parse with a text layer (no OCR needed in this set). Web advisories carry the overall residential rate and only the change in the generation charge. Only the ILECO III unbundled sheet carried both numbers.
2. **Facebook is closed from a server.** Both pages redirected to a login. Electric cooperatives that publish only on Facebook need another route: the cooperative's own site where one exists, the NEA or ERC filing, or a person with a logged in browser pasting the post. The build should count how many of the 142 are Facebook-only before promising coverage.
3. **"Price per kWh" needs a definition per source.** Overall residential rate (Meralco, Davao, Visayan, BENECO), VAT-exclusive total energy charges (ILECO III) and blended generation rate (Angeles, MORE) are different numbers. The schema's basis columns keep them apart; a comparison table must not mix them.
4. **Months are written five ways** (a dateline, "Billing Cycle", "Billing Month", "BILLING MONTH", a billing period "July 11 to August 10"). Each source needs a month rule; two of the eight needed the year from outside the sentence.
5. **The newest post is not always the newest month.** Visayan Electric's rates category listed a 2025 post above its 2026 ones; the first pick parsed correctly as October 2025 and was swapped for the August 2026 advisory. The collector should read the publication date, not the list order.
6. **Per-source rules are small.** Eight sources needed eight label rules of one line each plus three month rules. That is the shape of the four month build: a shared fetcher and text layer per format, one short rule set per utility, a review queue for the rows the second reader disputes.

## Cost and time
About 45 minutes of operator time including source discovery. Model cost: 16 flash calls over two runs, cents (route-model prices, not metered in this run). No paid scraper, no login, no proxy.

## Files
- `scripts/collect.py` the collector; `scripts/sources.json` the ten sources and their rules; `scripts/second_reader.py` the independent read.
- `out/rates.csv`, `out/rates.json` the table with evidence clips; `out/second_reader.json` the reader's answers; `out/reader_prompt_*.txt` what the reader saw.
- `sources/` the raw files as fetched (PDF, HTML) and their text, so every number can be traced without a network.

## Not checked
Facebook through a logged in browser (not attempted, by rule); OCR on image-only PDFs (none in this set); the ERC rate archive (erc.gov.ph answered 403 from this server); presyo.ph (did not answer); whether the Meralco "typical household" rate and the cooperatives' residential rates are the same definition ICSC uses; the other 132 utilities.
