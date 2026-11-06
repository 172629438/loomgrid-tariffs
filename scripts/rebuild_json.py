# -*- coding: utf-8 -*-
"""从 CSV 重建 province_tariff.json（schema 2.0）并刷新 meta.json 的统计字段。

数据以 CSV 为唯一事实源，JSON 是派生产物。改完 CSV 后跑一次：
    python scripts/rebuild_json.py
"""
from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def read_csv(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def num(v):
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _num(x: float):
    """整数小时保留为 int，半小时粒度保留 float。"""
    return int(x) if float(x).is_integer() else x


summary = read_csv("province_tariff_summary.csv")
periods = read_csv("province_tariff_periods.csv")

by_prov: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
for r in periods:
    by_prov[r["province"]][r["season"]].append(
        [r["months"], float(r["start_hour"]), float(r["end_hour"]), r["period_type"]])

provinces = {}
for r in summary:
    p = r["province"]
    groups = []
    for _season, segs in by_prov.get(p, {}).items():
        months = [int(x) for x in segs[0][0].split(",")]
        groups.append([months, [[_num(s[1]), _num(s[2]), s[3]] for s in segs]])
    groups.sort(key=lambda g: g[0][0])

    provinces[p] = {
        "peak": num(r["price_peak_cny_per_kwh"]),
        "flat": num(r["price_flat_cny_per_kwh"]),
        "valley": num(r["price_valley_cny_per_kwh"]),
        "sharp_peak": num(r.get("price_sharp_peak_cny_per_kwh")),
        "deep_valley": num(r.get("price_deep_valley_cny_per_kwh")),
        "demand": num(r["demand_charge_cny_per_kva_month"]),
        "price_zone": r.get("price_zone", ""),
        "grid_company": r.get("grid_company", ""),
        "voltage_level": r.get("voltage_level") or None,
        "proxy_regime": r.get("proxy_regime", ""),
        "market_regime": r.get("market_regime", ""),
        "market_source": r.get("market_source", ""),
        "mode": r.get("charging_mode", ""),
        "note": r.get("source_note", ""),
        "effective_from": r.get("effective_from") or None,
        "effective_to": r.get("effective_to") or None,
        "source_url": r.get("source_url") or None,
        "verify_status": r.get("verify_status", ""),
        "periods": groups,
    }

old_meta_path = DATA / "meta.json"
old_meta = json.loads(old_meta_path.read_text(encoding="utf-8")) if old_meta_path.exists() else {}

out = {
    "meta": {
        "dataset": "china-ci-tou-tariff",
        "schema_version": "2.0",
        "price_version": "2026-06",
        "last_updated": "2026-11-05",
        "check_months": 6,
        "province_count": len(provinces),
        "note": "schema 2.0 拆出适用主体/价区/尖峰深谷/来源与核实标记；价格数据版本仍为 2026-06，未重新取价",
    },
    "provinces": provinces,
}
(DATA / "province_tariff.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

NEW_REVIEW = [
    "18 省 effective_from 仍为空：未检索到可确认的官方生效日期，留空不臆造",
    "北京 16:00-17:00 尖峰落在官方平段 13:00-17:00 之内，文件表述与时段划分自相矛盾，未入库待核",
    "山东：本表为 2026 年公告时段（沿用 2025 年），但 2026-09-07 鲁发改价格函〔2026〕68号已调整低谷/高峰时长上限，时段未跟进",
    "广西：现行文件未确认（桂发改价格〔2023〕609号，另有 2024-11 动态调整征求意见稿），现有表「无尖峰」存疑",
    "广东：仅追溯到粤发改价格〔2021〕331号，与表内「夏谷0-9」口径不一致，2026 年新政文件待补",
    "广东四价区（珠三角六市/惠州/东西两翼/粤北）未拆行，分区价格未入库",
    "河北南网价格与时段为空值行，文号未获取",
    "尖峰价格列（price_sharp_peak）全空：时段结构已有，价格待取",
    "海南、青海的尖峰尚未入库",
    "山西、江西的节假日深谷（春节/劳动节/国庆 12-14 或 13-15）未入常规时段表：仅特定日期生效，需按日期查询",
    "时段表已完整对回官方原文的仅京、沪、闽、鲁、津、晋、赣 7 省；皖、豫、川、湘 4 省仅尖峰部分已核；其余 22 省未对原文",
    "全库 voltage_level 为空：未按 1-10kV / 35kV / 110kV 分档",
    "价格数值均为 2026-06 版本，未做 2026-07 至 2026-11 的月度代理购电跟踪",
    "21 省 market_regime 为 unknown：未核实其市场化用户是否仍执行政府核定分时电价",
]

meta = {
    "dataset": "china-ci-tou-tariff",
    "schema_version": "2.0",
    "price_version": "2026-06",
    "last_updated": "2026-11-05",
    "check_months": 6,
    "province_count": len(provinces),
    "provinces": list(provinces),
    "summary_rows": len(summary),
    "period_rows": len(periods),
    "dr_rows": len(read_csv("dr_subsidy.csv")),
    "regime_counts": dict(Counter(r.get("market_regime", "") for r in summary)),
    "verify_counts": dict(Counter(r.get("verify_status", "") for r in summary)),
    "effective_date_coverage": sum(1 for r in summary if (r.get("effective_from") or "").strip()),
    "needs_review": NEW_REVIEW,
    "issues": [],
}
old_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

print("json provinces:", len(provinces))
print("period rows:", len(periods))
print("effective_from coverage:", meta["effective_date_coverage"], "/", len(summary))
print("regime:", meta["regime_counts"])
print("verify:", meta["verify_counts"])
