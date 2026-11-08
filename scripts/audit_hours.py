# -*- coding: utf-8 -*-
"""时段时长自审：统计每省各档位的小时数，并对不合理分布告警。

用途
----
重写时段表后跑一遍，逐项核对「峰/平/谷各多少小时」是否与官方文件一致。
另外自动标出明显不合理的分布——例如某档位占 17 小时、或平段为 0 小时。
这类数值通常来自模板硬填，而非任何一份政策文件。

用法：
    python scripts/audit_hours.py            # 全量
    python scripts/audit_hours.py --suspect  # 只看可疑项
    python scripts/audit_hours.py --fail     # 检到可疑项时以退出码 1 结束（供 CI 使用）

默认只报告不阻断：库内暂存已知可疑表时，CI 不应因它们持续变红。
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
TIERS = ("peak", "flat", "valley", "sharp_peak", "deep_valley")
CN = {"peak": "峰", "flat": "平", "valley": "谷", "sharp_peak": "尖", "deep_valley": "深"}

# 单档位占全天超过这个小时数，视为可疑（正常分时机制中峰或谷极少超过 12h）
MAX_TIER_HOURS = 14


def main() -> int:
    only_suspect = "--suspect" in sys.argv

    with (DATA / "province_tariff_periods.csv").open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    with (DATA / "province_tariff_summary.csv").open(encoding="utf-8-sig", newline="") as fh:
        status = {r["province"]: r.get("period_table_status", "") for r in csv.DictReader(fh)}

    agg: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        agg[(r["province"], r["season"])][r["period_type"]] += float(r["duration_h"])

    suspects = []
    print(f"{'省份':<6}{'季节':<22}{'峰':>5}{'平':>5}{'谷':>5}{'尖':>5}{'深':>5}{'合计':>7}  状态")
    print("-" * 78)
    for key in sorted(agg):
        prov, season = key
        d = agg[key]
        total = sum(d.values())
        st = status.get(prov, "")
        row = (f"{prov:<6}{season[:20]:<22}"
               + "".join(f"{d.get(t, 0):>5.0f}" for t in TIERS)
               + f"{total:>7.0f}  {st}")

        bad = []
        for t in TIERS:
            if d.get(t, 0) > MAX_TIER_HOURS:
                bad.append(f"{CN[t]}段 {d[t]:.0f}h 过长")
        if d.get("flat", 0) == 0 and d.get("peak", 0) > 0:
            bad.append("平段为 0")
        if abs(total - 24) > 1e-6:
            bad.append(f"合计 {total}h ≠ 24")
        if bad:
            suspects.append((prov, season, bad))
            row += "  ← " + "；".join(bad)

        if not only_suspect or bad:
            print(row)

    print()
    if suspects:
        print(f"⚠️  {len(suspects)} 组时段分布可疑：")
        for prov, season, bad in suspects:
            print(f"  {prov} / {season}：{'；'.join(bad)}")
        print("\n这些分布通常意味着数据来自模板套用，应核回官方文件后再使用。")
        print("（默认不阻断；加 --fail 则以退出码 1 结束）")
        return 1 if "--fail" in sys.argv else 0
    print("✅ 未发现异常时长分布")
    return 0


if __name__ == "__main__":
    sys.exit(main())
