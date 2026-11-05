# -*- coding: utf-8 -*-
"""电价数据集自检。

不看数据对不对（那要人对照政策文件），只看数据自不自洽——
一份自相矛盾的表，无论抄得多认真都是错的。

检查项：
  1. summary.csv 与 province_tariff.json 的省份集合一致
  2. 价格单调：peak > flat > valley，且均 > 0
  3. 每个省每个季节的时段无缝覆盖 0–24 小时，无空洞无重叠
  4. duration_h 求和等于 24
  5. period_type 只在已知词表内
  6. 必填字段非空

用法：
    python validate.py [data_dir]

退出码 0 = 全过；1 = 有 FAIL。
WARN 不算失败，但会在输出里列出来。
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "data"

KNOWN_TYPES = {"peak", "flat", "valley", "sharp_peak", "deep_valley",
               "charge", "discharge"}
KNOWN_REGIMES = {"regulated", "market", "mixed", "pending", "unknown"}
KNOWN_VERIFY = {"none", "policy", "price", "full"}

fails: list[str] = []
warns: list[str] = []


def fail(msg: str) -> None:
    fails.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def read_csv(name: str) -> list[dict]:
    path = DATA / name
    if not path.exists():
        fail(f"缺文件：{name}")
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


summary = read_csv("province_tariff_summary.csv")
periods = read_csv("province_tariff_periods.csv")
dr = read_csv("dr_subsidy.csv")

nest_path = DATA / "province_tariff.json"
nested: dict = {}
if not nest_path.exists():
    fail("缺文件：province_tariff.json")
else:
    nested = json.loads(nest_path.read_text(encoding="utf-8")).get("provinces", {})

# ── 1. 省份集合一致 ──
sum_set = {r["province"] for r in summary}
nest_set = set(nested)
if sum_set != nest_set:
    fail(f"省份集合不一致：summary 独有 {sorted(sum_set - nest_set)}；"
         f"json 独有 {sorted(nest_set - sum_set)}")
if len(sum_set) != len(summary):
    fail(f"summary.csv 存在重复省份：{len(summary)} 行 / {len(sum_set)} 个省份")

# ── 2. 价格单调 ──
placeholder: list[str] = []
for r in summary:
    prov = r["province"]
    raw = [(r.get("price_peak_cny_per_kwh") or "").strip(),
           (r.get("price_flat_cny_per_kwh") or "").strip(),
           (r.get("price_valley_cny_per_kwh") or "").strip()]

    # 允许整行为占位（价格全空），但必须显式声明未核实
    if not any(raw):
        placeholder.append(prov)
        if (r.get("verify_status") or "").strip() == "full":
            fail(f"{prov}：价格为空的占位行却标记 verify_status=full")
        warn(f"{prov}：价格为占位空值（结构已登记、数值未取）")
    else:
        if not all(raw):
            fail(f"{prov}：峰/平/谷价格只有部分填写 {raw}")
            continue
        try:
            peak, flat, valley = (float(x) for x in raw)
        except ValueError:
            fail(f"{prov}：价格字段无法解析为数字")
            continue
        if min(peak, flat, valley) <= 0:
            fail(f"{prov}：存在非正价格（peak={peak} flat={flat} valley={valley}）")
        if not (peak > flat > valley):
            fail(f"{prov}：价格未满足 peak>flat>valley（{peak}/{flat}/{valley}）")

    if not r.get("source_note", "").strip():
        warn(f"{prov}：source_note 为空，无法追溯政策出处")
    if not (r.get("effective_from") or "").strip():
        warn(f"{prov}：effective_from 为空")

    # 新增枚举词表
    mr = (r.get("market_regime") or "").strip()
    if mr and mr not in KNOWN_REGIMES:
        fail(f"{prov}：未知 market_regime {mr!r}")
    vs = (r.get("verify_status") or "").strip()
    if vs and vs not in KNOWN_VERIFY:
        fail(f"{prov}：未知 verify_status {vs!r}")
    if mr == "market" and not (r.get("source_url") or "").strip():
        warn(f"{prov}：标记为市场化定价却无 source_url")

# ── 3~5. 时段连续性 ──
by_group: dict[tuple[str, str], list[dict]] = defaultdict(list)
for r in periods:
    by_group[(r["province"], r["season"])].append(r)

# 有 summary 行却没有任何时段组（占位省），单独提示而不当作错误
no_period = sorted(sum_set - {k[0] for k in by_group})
for p in no_period:
    warn(f"{p}：无时段划分记录（价格与时段均待补）")

for (prov, season), rows in sorted(by_group.items()):
    # 5. 类型词表
    for r in rows:
        if r["period_type"] not in KNOWN_TYPES:
            fail(f"{prov}/{season}：未知 period_type {r['period_type']!r}")

    # 3. 展开成小时占用，检查覆盖与重叠
    owner: dict[int, str] = {}
    for r in rows:
        try:
            start, end = int(r["start_hour"]), int(r["end_hour"])
        except ValueError:
            fail(f"{prov}/{season}：start/end 非整数")
            continue
        hours = list(range(start, 24)) + list(range(0, end)) if end < start else list(range(start, end))
        if not hours:
            fail(f"{prov}/{season}：时段 {start}→{end} 为空")
        for h in hours:
            if h in owner:
                fail(f"{prov}/{season}：{h:02d} 时被两段同时占用"
                     f"（{owner[h]} 与 {r['period_type']}）")
            owner[h] = r["period_type"]

    missing = [h for h in range(24) if h not in owner]
    if missing:
        fail(f"{prov}/{season}：未覆盖的小时 {missing}")

    # 4. duration 求和
    total = 0.0
    for r in rows:
        try:
            start, end = int(r["start_hour"]), int(r["end_hour"])
        except ValueError:
            continue
        total += (end - start) % 24 or 24
    if abs(total - 24.0) > 1e-6:
        fail(f"{prov}/{season}：时长合计 {total} h ≠ 24 h")

# ── 6. duration_h 字段自洽 ──
for r in periods:
    try:
        start, end = int(r["start_hour"]), int(r["end_hour"])
        declared = float(r["duration_h"])
    except (TypeError, ValueError):
        fail(f"{r['province']}/{r['season']}：duration_h 非数字")
        continue
    expected = (end - start) % 24 or 24
    if abs(declared - expected) > 1e-6:
        fail(f"{r['province']}/{r['season']}：duration_h 声明 {declared}，应为 {expected}")

# ── 汇总 ──
print(f"data dir     : {DATA}")
print(f"provinces    : {len(sum_set)}")
print(f"placeholder  : {len(placeholder)} {placeholder}")
print(f"no-period    : {len(no_period)} {no_period}")
print(f"period rows  : {len(periods)}")
print(f"season groups: {len(by_group)}")
print(f"dr rows      : {len(dr)}")
print()

for w in warns:
    print(f"WARN  {w}")
if warns:
    print()

for f in fails:
    print(f"FAIL  {f}")

if fails:
    print(f"\n❌ {len(fails)} 项失败，{len(warns)} 项警告")
    sys.exit(1)

print(f"✅ 全部通过（{len(warns)} 项警告）")
