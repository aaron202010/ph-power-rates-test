#!/usr/bin/env python3
"""BetterGov Energy track, prototype test (2026-10-20): collect residential electricity rates from ten utility
publications in three formats (PDF, web page, Facebook page) into one table.

One collector per format (fetch + text extraction). One small rule set per source (which label carries which number),
because every utility words its table differently. Nothing is guessed: a field the source does not state is written as
"not in source", a page that needs a login is written as "unreachable". Every row keeps the source URL, the fetch time
and the exact text clip the number came from, so a reviewer can check it without opening the file.

usage: collect.py [--sources sources.json] [--out out/]  (reads the live sources; saves raw files under sources/)
"""
import json, re, ssl, sys, os, subprocess, html, datetime, hashlib, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36", "Accept": "*/*"}
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
FIELDS = ["utility", "month", "residential_rate_php_per_kwh", "rate_basis", "generation_charge_php_per_kwh",
          "generation_basis", "source_url", "fetched_at_utc", "format", "status", "evidence"]


def fetch(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40, context=CTX)
    return r.read(), r.geturl(), r.headers.get("content-type", "")


def text_of_pdf(raw, path):
    open(path, "wb").write(raw)
    return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout


def text_of_html(raw, path):
    open(path, "wb").write(raw)
    t = raw.decode("utf-8", "replace")
    b = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    b = re.sub(r"<br\s*/?>|</p>|</tr>|</li>|</h\d>|</div>|</td>", "\n", b, flags=re.I)
    b = html.unescape(re.sub(r"<[^>]+>", " ", b))
    return "\n".join(re.sub(r"\s+", " ", l).strip() for l in b.split("\n") if l.strip())


def find(text, pattern, group=1):
    """First match of a label pattern; returns (value, the line it sat on) or (None, None)."""
    for line in text.split("\n"):
        m = re.search(pattern, line, re.I)
        if m:
            return m.group(group), line.strip()
    m = re.search(pattern, text, re.I | re.S)  # label and number on different lines
    if m:
        s = max(0, m.start() - 60); return m.group(group), re.sub(r"\s+", " ", text[s:m.end() + 40]).strip()
    return None, None


def collect(src):
    row = {k: "" for k in FIELDS}
    row.update(utility=src["utility"], source_url=src["url"], format=src["format"],
               fetched_at_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    name = hashlib.md5(src["url"].encode()).hexdigest()[:8]
    try:
        raw, final_url, ctype = fetch(src["url"])
    except Exception as e:  # noqa: BLE001
        row.update(status="unreachable", evidence=f"fetch error: {str(e)[:120]}"); return row
    if src["format"] == "facebook" or "facebook.com" in final_url:
        if "login" in final_url or b"login" in raw[:4000].lower():
            row.update(status="unreachable", evidence=f"redirected to a login page: {final_url[:90]}")
            open(f"{ROOT}/sources/{name}.html", "wb").write(raw); return row
    if src["format"] == "pdf" or "pdf" in ctype:
        text = text_of_pdf(raw, f"{ROOT}/sources/{name}.pdf")
    else:
        text = text_of_html(raw, f"{ROOT}/sources/{name}.html")
    open(f"{ROOT}/sources/{name}.txt", "w").write(text)
    clips = []
    month, clip = (None, None)
    if src.get("month_pattern"):
        m = re.search(src["month_pattern"], text, re.I)
        if m:
            month = " ".join(g for g in m.groups() if g); clip = re.sub(r"\s+", " ", text[max(0, m.start() - 40):m.end() + 40]).strip()
    if month and not re.search(r"\d{4}", month):  # the sentence names the month only; take the year from the dateline or the page metadata
        y = re.search(src["year_pattern"], text, re.I) if src.get("year_pattern") else None
        y = y or (re.search(src["year_pattern_html"], raw.decode("utf-8", "replace")) if src.get("year_pattern_html") else None)
        month = f"{month} {y.group(1)}" if y else f"{month} (year not stated in the text)"
        clip = (clip or "") + (f" || year from: {y.group(0)[:80]}" if y else "")
    row["month"] = (month or "not in source").title().replace("Of ", "of "); clips.append(f"month: {clip}")
    for field, basis in (("residential_rate_php_per_kwh", "rate_basis"), ("generation_charge_php_per_kwh", "generation_basis")):
        rule = src.get(field)
        if not rule:
            row[field] = "not in source"; row[basis] = src.get(basis, ""); continue
        val, clip = find(text, rule)
        row[field] = val if val else "parse failed"
        row[basis] = src.get(basis, "")
        clips.append(f"{field.split('_')[0]}: {clip or 'no line matched ' + rule}")
    stated = [f for f in ("residential_rate_php_per_kwh", "generation_charge_php_per_kwh") if row[f] != "not in source"]
    failed = [f for f in stated if row[f] == "parse failed"]
    row["status"] = "parsed" if stated and not failed else ("parse failed" if failed else "no rate field in source")
    row["evidence"] = " || ".join(clips)
    return row


def main():
    srcs = json.load(open(sys.argv[sys.argv.index("--sources") + 1] if "--sources" in sys.argv else f"{HERE}/sources.json"))
    rows = [collect(s) for s in srcs]
    import csv
    with open(f"{ROOT}/out/rates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    json.dump(rows, open(f"{ROOT}/out/rates.json", "w"), indent=1, ensure_ascii=False)
    for r in rows:
        print(f"{r['status']:<22} {r['format']:<9} {r['utility']:<22} {r['month']:<16} rate {r['residential_rate_php_per_kwh']:<14} gen {r['generation_charge_php_per_kwh']}")


if __name__ == "__main__":
    main()
