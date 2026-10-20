#!/usr/bin/env python3
"""Independent second read: deepseek flash (through route-model) extracts the same fields from each saved source text,
without seeing the collector's answer. compare.py then lines the two up. Cents per run."""
import json, subprocess, os, concurrent.futures as cf, re, hashlib, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = json.load(open(f"{ROOT}/out/rates.json"))
CALL = ["/usr/bin/python3", "/root/.claude/skills/route-model/scripts/call.py", "deepseek/deepseek-v4-flash"]
def one(r):
    name = hashlib.md5(r["source_url"].encode()).hexdigest()[:8]
    f = f"{ROOT}/sources/{name}.txt"
    if not os.path.exists(f):
        return {"source_url": r["source_url"], "reader": "no text (unreachable)"}
    text = open(f).read()
    if len(text) > 14000:  # keep the lines that carry numbers and labels
        keep = [l for l in text.split("\n") if re.search(r"kwh|generation|residential|total|billing|month|2026|rate", l, re.I)]
        text = "\n".join(keep)[:14000]
    prompt = ("Read this electricity rate publication from a Philippine distribution utility. Return ONLY a JSON object with keys: "
              "month (the billing month and year the publication is for, as written), residential_rate (the overall residential rate in PhP per kWh if the text states one, else \"not in source\"), "
              "residential_rate_quote (the exact text that states it, max 25 words, or \"\"), generation_charge (the generation charge or generation rate in PhP per kWh if stated as a level, else \"not in source\"), "
              "generation_quote (exact text, max 25 words, or \"\"). Rules: copy numbers exactly as printed, never compute or round, a change (increase or decrease) is not a level, "
              "if several residential numbers exist pick the one labelled as the overall or total residential rate and say which in the quote.\n\nTEXT:\n" + text)
    pf = f"{ROOT}/out/reader_prompt_{name}.txt"; open(pf, "w").write(prompt)
    out = subprocess.run(CALL + [pf, "--effort", "low", "--no-gates"], capture_output=True, text=True, timeout=300).stdout
    try:
        j = json.loads(out[out.index("{"): out.rindex("}") + 1])
    except Exception:
        j = {"reader": "unparsable: " + out[:200]}
    j["source_url"] = r["source_url"]; return j
with cf.ThreadPoolExecutor(4) as ex:
    res = list(ex.map(one, rows))
json.dump(res, open(f"{ROOT}/out/second_reader.json", "w"), indent=1, ensure_ascii=False)
for a, b in zip(rows, res):
    print(f"{a['utility']:<24} collector: {a['month']:<14} {a['residential_rate_php_per_kwh']:<14} {a['generation_charge_php_per_kwh']:<14} | reader: {str(b.get('month','-')):<16} {str(b.get('residential_rate','-')):<14} {str(b.get('generation_charge','-'))}")
