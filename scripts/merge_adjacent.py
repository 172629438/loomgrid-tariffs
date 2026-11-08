# -*- coding: utf-8 -*-
"""合并相邻的同类型时段（如 0-9:valley + 9-17:valley -> 0-17:valley）。
纯格式清洗，不改变任何时段语义。
"""
import csv, io, os
from collections import defaultdict

DATA = r"C:\Users\Administrator\.hanako\repos\172629438__loomgrid-tariffs\data"
path = os.path.join(DATA, "province_tariff_periods.csv")

with io.open(path, encoding="utf-8-sig", newline="") as fh:
    rows = list(csv.DictReader(fh))
cols = list(rows[0].keys())

groups = defaultdict(list)
for r in rows:
    groups[(r["province"], r["season"])].append(r)

out = []
merged_count = 0
for (prov, season), segs in groups.items():
    segs = sorted(segs, key=lambda x: float(x["start_hour"]))
    cur = None
    merged = []
    for r in segs:
        a, b, t = float(r["start_hour"]), float(r["end_hour"]), r["period_type"]
        if cur and cur["type"] == t and abs(cur["end"] - a) < 1e-9:
            cur["end"] = b
            merged_count += 1
        else:
            if cur:
                merged.append(cur)
            cur = {"start": a, "end": b, "type": t,
                   "months": r["months"], "basis": r.get("source_basis", "")}
    if cur:
        merged.append(cur)

    for m in merged:
        dur = (m["end"] - m["start"]) % 24 or 24
        out.append({
            "province": prov, "season": season, "months": m["months"],
            "start_hour": (str(int(m["start"])) if float(m["start"]).is_integer() else str(m["start"])),
            "end_hour": (str(int(m["end"])) if float(m["end"]).is_integer() else str(m["end"])),
            "duration_h": (str(int(dur)) if float(dur).is_integer() else str(dur)),
            "period_type": m["type"],
            "source_basis": m["basis"],
        })

with io.open(path, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in out:
        w.writerow({c: r.get(c, "") for c in cols})

print(f"合并相邻同类型段 {merged_count} 处；行数 {len(rows)} -> {len(out)}")
