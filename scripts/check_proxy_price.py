# -*- coding: utf-8 -*-
"""月度代理购电价格巡检：把「当月价格快照」与库内数据比对，产出差异报告。

设计原则
--------
取数与比对分离。取数（爬各省电网公告）不稳定、格式各异、常需人工核对，
因此不由本脚本强行完成；脚本负责的是**确定性比对**与**差异报告**，
让「变了」这件事每次都能被看见，而不是靠人记得去查。

用法
----
1) 从当月公告抄录一份快照（模板见 scripts/price_snapshot_template.csv）
2) 比对：
       python scripts/check_proxy_price.py --snapshot snapshot-2026-11.csv
3) 自测（造一份只改一个省的价格，验证脚本能抓到）：
       python scripts/check_proxy_price.py --demo

退出码：0 = 无差异；1 = 有差异（CI 里可据此报警）。

快照列
------
province, price_zone, month, peak, flat, valley, sharp_peak, deep_valley, source_url, note
价格留空表示该档未列示或未执行；整行价格全空的行会被跳过并提示。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_TOL = 0.001  # 元/kWh，公告精度通常到 0.0001


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def num(v) -> float | None:
    v = (v or "").strip() if isinstance(v, str) else v
    if v in ("", None):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_current() -> dict[tuple[str, str], dict]:
    rows = read_csv(DATA / "province_tariff_summary.csv")
    cur: dict[tuple[str, str], dict] = {}
    for r in rows:
        key = (r["province"].strip(), (r.get("price_zone") or "").strip())
        cur[key] = {
            "peak": num(r.get("price_peak_cny_per_kwh")),
            "flat": num(r.get("price_flat_cny_per_kwh")),
            "valley": num(r.get("price_valley_cny_per_kwh")),
            "sharp_peak": num(r.get("price_sharp_peak_cny_per_kwh")),
            "deep_valley": num(r.get("price_deep_valley_cny_per_kwh")),
            "effective_from": (r.get("effective_from") or "").strip(),
        }
    return cur


def load_snapshot(path: Path) -> tuple[dict[tuple[str, str], dict], list[str]]:
    snap: dict[tuple[str, str], dict] = {}
    skipped: list[str] = []
    for r in read_csv(path):
        prov = (r.get("province") or "").strip()
        if not prov:
            continue
        vals = {k: num(r.get(k)) for k in ("peak", "flat", "valley", "sharp_peak", "deep_valley")}
        if all(v is None for v in vals.values()):
            skipped.append(prov)
            continue
        key = (prov, (r.get("price_zone") or "").strip())
        snap[key] = {**vals,
                     "month": (r.get("month") or "").strip(),
                     "source_url": (r.get("source_url") or "").strip()}
    return snap, skipped


TIERS = ("peak", "flat", "valley", "sharp_peak", "deep_valley")
TIER_CN = {"peak": "高峰", "flat": "平段", "valley": "低谷",
           "sharp_peak": "尖峰", "deep_valley": "深谷"}


def diff(cur: dict, snap: dict, tol: float) -> dict:
    res = {"price_changes": [], "new_zones": [], "missing_in_snapshot": [],
           "zone_mismatch": []}

    provs_cur = {k[0] for k in cur}
    provs_snap = {k[0] for k in snap}
    res["missing_in_snapshot"] = sorted(provs_cur - provs_snap)
    res["new_zones"] = sorted(provs_snap - provs_cur)

    # 同一省份库内只有一行、快照给了另一个价区名：提示价区口径不一致
    cur_zones = {k[0]: k[1] for k in cur}
    for (p, z) in snap:
        if p in cur_zones and cur_zones[p] and z and z != cur_zones[p] \
                and (p, z) not in cur:
            res["zone_mismatch"].append((p, cur_zones[p], z))

    for key, s in snap.items():
        c = cur.get(key)
        if not c:
            continue
        for t in TIERS:
            a, b = c.get(t), s.get(t)
            if a is None or b is None:
                if a is None and b is not None:
                    res["price_changes"].append(
                        {"province": key[0], "zone": key[1], "tier": t,
                         "old": None, "new": b, "delta": None, "kind": "新增值"})
                continue
            d = round(b - a, 6)
            if abs(d) > tol:
                res["price_changes"].append(
                    {"province": key[0], "zone": key[1], "tier": t,
                     "old": a, "new": b, "delta": d,
                     "kind": "上涨" if d > 0 else "下降"})
    return res


def render(res: dict, snap_month: str, tol: float) -> str:
    lines = []
    n = len(res["price_changes"])
    lines.append(f"# 代理购电价格巡检 · {snap_month or '未标注月份'}")
    lines.append("")
    lines.append(f"生成时间：{dt.datetime.now():%Y-%m-%d %H:%M}　比对容差：±{tol} 元/kWh")
    lines.append("")

    if n == 0 and not res["new_zones"] and not res["zone_mismatch"]:
        lines.append("**结论：与库内数据一致，无需变更。**")
    else:
        lines.append(f"**结论：检出 {n} 处价格变动"
                     f"{'、' + str(len(res['new_zones'])) + ' 个新增价区' if res['new_zones'] else ''}，"
                     "需人工确认后发布新版本。**")

    if res["price_changes"]:
        lines += ["", "## 价格变动", "",
                  "| 省份 | 价区 | 档位 | 库内 | 快照 | 差额 | 方向 |",
                  "|---|---|---|---|---|---|---|"]
        for c in sorted(res["price_changes"], key=lambda x: (x["province"], x["tier"])):
            old = "-" if c["old"] is None else "%.4f" % c["old"]
            delta = "-" if c["delta"] is None else "%+.4f" % c["delta"]
            lines.append(
                "| %s | %s | %s | %s | %.4f | %s | %s |" % (
                    c["province"], c["zone"] or "-",
                    TIER_CN.get(c["tier"], c["tier"]),
                    old, c["new"], delta, c["kind"]))

    if res["new_zones"]:
        lines += ["", "## 快照中多出的省份/价区（库内无对应）"]
        for p, z in res["new_zones"]:
            lines.append(f"- {p} / {z or '-'}")

    if res["zone_mismatch"]:
        lines += ["", "## 价区口径不一致（需先统一口径再比对）"]
        for p, a, b in res["zone_mismatch"]:
            lines.append(f"- {p}：库内 `{a}` ↔ 快照 `{b}`")

    if res["missing_in_snapshot"]:
        lines += ["", f"## 快照未覆盖（{len(res['missing_in_snapshot'])} 个，沿用库内旧值）",
                  "、" .join(res["missing_in_snapshot"])]

    lines += ["", "---", "",
              "本报告只陈述差异，不修改任何数据。确认无误后按 CHANGELOG 维护约定发新版本。"]
    return "\n".join(lines) + "\n"


def make_demo_snapshot(dest: Path) -> Path:
    """造一份「与库内相同、但把一个省的高峰价改动 0.02」的快照。"""
    cur = load_current()
    rows = []
    for (p, z), v in cur.items():
        if v["peak"] is None:
            continue
        peak = v["peak"]
        if p == "浙江":
            peak = round(peak + 0.02, 4)
        rows.append({
            "province": p, "price_zone": z, "month": "demo",
            "peak": f"{peak:.4f}" if peak is not None else "",
            "flat": f"{v['flat']:.4f}" if v["flat"] is not None else "",
            "valley": f"{v['valley']:.4f}" if v["valley"] is not None else "",
            "sharp_peak": "", "deep_valley": "",
            "source_url": "", "note": "demo",
        })
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="代理购电价格巡检比对")
    ap.add_argument("--snapshot", type=Path, help="当月价格快照 CSV")
    ap.add_argument("--demo", action="store_true", help="自测：造一份只改一省价格的快照")
    ap.add_argument("--tol", type=float, default=DEFAULT_TOL, help="比对容差，默认 0.001")
    ap.add_argument("--out", type=Path, help="报告输出路径")
    ap.add_argument("--json", action="store_true", help="同时输出 JSON")
    args = ap.parse_args()

    if args.demo:
        snap_path = make_demo_snapshot(ROOT / "scripts" / "_demo_snapshot.csv")
        print(f"[demo] 已生成 {snap_path}（浙江高峰价 +0.02）")
    elif args.snapshot:
        snap_path = args.snapshot
    else:
        ap.print_help()
        return 2

    cur = load_current()
    snap, skipped = load_snapshot(snap_path)
    if skipped:
        print(f"提示：{len(skipped)} 行价格全空已跳过：{'、'.join(skipped)}")

    res = diff(cur, snap, args.tol)
    month = next((v.get("month") for v in snap.values() if v.get("month")), "") or ""
    report = render(res, month, args.tol)

    tag = month or dt.date.today().strftime("%Y%m")
    out = args.out or (ROOT / "reports" / ("price-diff-%s.md" % tag))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"[报告] {out}")

    if args.json:
        jp = out.with_suffix(".json")
        jp.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[JSON] {jp}")

    return 1 if (res["price_changes"] or res["new_zones"]) else 0


if __name__ == "__main__":
    sys.exit(main())
