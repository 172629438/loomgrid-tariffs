# 中国省级分时电价数据集 · China Provincial TOU Tariff Dataset

**32 个省级行政区 · 峰平谷电价 · 分季节时段表 · 需求响应补贴**
**32 provincial-level regions · peak/flat/valley prices · seasonal period tables · demand-response subsidies**

[![Regions](https://img.shields.io/badge/regions-32-2f6b4f?style=flat-square)](#覆盖范围)
[![Periods](https://img.shields.io/badge/period_records-311-2f6b4f?style=flat-square)](#文件结构)
[![Price version](https://img.shields.io/badge/price_version-2026--06-9a7b2e?style=flat-square)](#数据版本与时效)
[![License](https://img.shields.io/badge/license-MIT-2f6b4f?style=flat-square)](LICENSE)

> 一份可以直接 `read_csv` 拿来算储能、光伏、需量管理的中国分时电价表。
> 每个省都带**政策文号出处**——这是它和网上转载版本最大的区别。
>
> A machine-readable dataset of China's time-of-use (TOU) electricity tariffs, with **policy document citations** for every province.

---

## English summary

China's industrial & commercial (C&I) electricity tariffs are **time-of-use based**: each day is split into peak / flat / valley segments, and every province defines its own segment boundaries, its own seasonal groupings, and its own price levels. There is no single national file — practitioners rebuild this table from provincial NDRC notices, by hand, for every project.

This dataset collects the result of that work for **32 provincial-level regions**, as of **price version 2026-06**:

- `data/province_tariff_summary.csv` — one row per region: peak/flat/valley price, demand charge, charging-cycle mode, policy citation
- `data/province_tariff_periods.csv` — long format: region × season × time segment (311 records)
- `data/province_tariff.json` — full nested structure, drop-in for application code
- `data/dr_subsidy.csv` — demand-response subsidy standards (5 regions with published rates)

Built and maintained by the author of [LoomGrid](https://github.com/172629438/loomgrid), a C&I BESS sizing studio, because this table gets rebuilt from scratch on every project.

**Read the caveats in [数据边界](#数据边界) before using it for anything contractual.**

---

## 覆盖范围

32 个省级行政区，按电网区域划分：

| 区域 | 省级行政区 |
|---|---|
| 华东 | 上海 · 江苏 · 浙江 · 安徽 · 福建 · 江西 · 山东 |
| 华南 | 广东 · 广西 · 海南 |
| 华中 | 河南 · 湖北 · 湖南 |
| 华北 | 北京 · 天津 · 河北 · 山西 · 蒙东 · 蒙西 |
| 西北 | 陕西 · 甘肃 · 青海 · 宁夏 · 新疆 |
| 西南 | 四川 · 重庆 · 云南 · 贵州 · 西藏 |
| 东北 | 辽宁 · 吉林 · 黑龙江 |

---

## 快速使用

```python
import pandas as pd

# 一省一行：拿来做敏感性分析、画价格对比
summary = pd.read_csv("data/province_tariff_summary.csv")
summary[["province", "price_peak_cny_per_kwh", "price_valley_cny_per_kwh"]] \
    .assign(spread=lambda d: d.price_peak_cny_per_kwh - d.price_valley_cny_per_kwh) \
    .sort_values("spread", ascending=False).head(10)
```

```python
# 时段长表：还原某个省某个月的 24 小时电价序列
periods = pd.read_csv("data/province_tariff_periods.csv")
zj = periods[(periods.province == "浙江") & (periods.months.str.contains("7"))]
for _, r in zj.iterrows():
    print(f"{int(r.start_hour):02d}:00–{int(r.end_hour):02d}:00  {r.period_type}")
```

```
00:00–08:00  valley
08:00–11:00  flat
11:00–14:00  valley
14:00–16:00  flat
16:00–18:00  peak
18:00–22:00  peak
22:00–23:00  peak
23:00–24:00  flat
```

---

## 文件结构

```
data/
├── province_tariff_summary.csv    32 行 · 一省一行 · 价格/需量/模式/出处
├── province_tariff_periods.csv   311 行 · 省份×季节×时段 长表
├── province_tariff.json           完整嵌套结构（含原始 periods 字段）
├── dr_subsidy.csv                  5 行 · 需求响应补贴
└── meta.json                      版本 / 省份清单 / 生成元信息
```

### `province_tariff_summary.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| `province` | str | 省级行政区名（中文，如 `浙江`） |
| `price_peak_cny_per_kwh` | float | 高峰电价，元/kWh |
| `price_flat_cny_per_kwh` | float | 平段电价，元/kWh |
| `price_valley_cny_per_kwh` | float | 低谷电价，元/kWh |
| `demand_charge_cny_per_kva_month` | float | 需量（基本）电费，元/kVA·月 |
| `charging_mode` | str | 推荐充放模式：`一充一放` / `两充两放` / `现货市场` |
| `effective_from` | str \| blank | 政策生效日（`YYYY-MM-DD`），未知则留空 |
| `source_note` | str | **政策文号与要点**，如「浙发改价格〔2026〕112号(2026.7.1生效)」 |
| `seasonal_periods` | bool | 是否分季节定义时段（`yes`/`no`） |

### `province_tariff_periods.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| `province` | str | 省级行政区名 |
| `season` | str | 季节标签，如 `2-11月等8个月` / `全年` |
| `months` | str | 该季节对应的月份，逗号分隔（`2,3,4,...`） |
| `start_hour` | int | 时段起点（0–24） |
| `end_hour` | int | 时段终点（0–24）；`end < start` 表示跨午夜 |
| `duration_h` | float | 时长（小时） |
| `period_type` | str | `peak` / `flat` / `valley` |

> 跨午夜提示：`(23, 6, 'valley')` 表示 23:00 至次日 06:00，`end_hour < start_hour`。
> `duration_h` 已按跨午夜修正。

---

## 数据版本与时效

| 项 | 值 |
|---|---|
| 数据版本 | `2026-06` |
| 建议复核周期 | 6 个月 |
| 数据来源 | 各省发改委 / 能源局分时电价公告，人工整理 |

中国分时电价调整频繁——仅 2026 年上半年就有浙江、江苏、安徽、山东等多省调整峰谷时段或取消上午高峰。**任何超过 6 个月未复核的电价数据，都不应直接用于报价。**

本项目内置的 `meta.json` 里带 `price_version` 与 `check_months` 字段，应用层可据此做时效告警。

---

## 数据边界

诚实交代这份数据**不覆盖**什么。做商务决策前请逐条确认。

1. **单一电压等级参考价。** `price_*` 是各省代表性的工商业电价水平，**不是**分电压等级（1–10kV / 35kV / 110kV）的完整目录电价。实际结算价按电压等级与用户类别不同，差异可达 10–20%。
2. **不含代理购电浮动。** 2023 年后多数省份工商业用户电价由「代理购电价格 + 输配电价 + 系统运行费 + 政府性基金」构成，且按月浮动。本数据集给出的是结构性参考值，不含月度浮动因子。
3. **尖峰与深谷未单独列价。** 部分省份对尖峰时段加价、深谷时段折价，本表只保留 `peak`/`flat`/`valley` 三档；尖峰时段在 `period_type` 中仍记为 `peak`。
4. **不含容量电价机制差异。** 需量电费按元/kVA·月给出统一参考值，实际按变压器容量计费与按最大需量计费的规则各省不同（如 114 号文相关条款）。
5. **现货市场省份为占位。** 已取消固定分时电价的省份，`charging_mode` 记为 `现货市场`，其时段表仅供参考，不代表结算规则。
6. **需求响应补贴仅 5 省。** 其余省份未收录（未收录 ≠ 无政策）。
7. **人工整理，可能有误。** 每一省都标注了出处，但整理过程难免出错。发现错误请开 issue，注明省份 + 政策文号 + 正确值。

**结论：本数据集适合测算、对比、做原型、教学；不适合作为合同附件或结算依据。**

---

## 数据来源

数据整理自各省发改委、能源局公开的分时电价政策文件。每省的政策依据记录在 `source_note` 字段中，例如：

| 省份 | source_note 摘录 |
|---|---|
| 浙江 | 浙发改价格〔2026〕112号(2026.7.1生效);取消上午高峰,午谷3h(11-14),晚高峰16-23 |
| 安徽 | 皖2025.7新政3季模式;春秋午谷11-14/夏谷2-9+11-13/冬谷12-14;尖峰7-8月20-22 |
| 江苏 | 2025.6新政;夏冬午谷2h/春秋午谷4h(10-14) |

> 本数据集是整理成果，不是官方发布物。引用原始政策请以各省发改委官网文件为准。

---

## 更新机制

```bash
# 编辑 data/ 下的 CSV 与 JSON（两者需保持一致）
# 更新 meta.json 的 price_version 与 last_updated
# 在 CHANGELOG.md 里记一笔改了哪几个省、依据哪份文件
```

收到某省电价调整公告时，最小改动路径是：
1. 改 `province_tariff_summary.csv` 对应行的价格与 `source_note`
2. 改 `province_tariff_periods.csv` 对应省份的时段行
3. 同步 `province_tariff.json`
4. `meta.json` 的 `price_version` 推进
5. `CHANGELOG.md` 记录

---

## 引用

如果这份数据帮到了你的研究或项目，可以这样引用（也欢迎直接 star）：

```bibtex
@misc{loomgrid_tariff_2026,
  title  = {China Provincial TOU Tariff Dataset},
  author = {LoomGrid},
  year   = {2026},
  note   = {32 provincial-level regions, price version 2026-06},
  url    = {https://github.com/172629438/loomgrid-tariffs}
}
```

机器可读的引用元数据见 [`CITATION.cff`](CITATION.cff)。

---

## 相关项目

- **[LoomGrid](https://github.com/172629438/loomgrid)** — 工商业储能测算工作台。这份电价表最初就是它的内置数据源，从 3.6 万行主程序里剥离而来。
- 算法层可独立使用：`algorithms/periods.py` 负责时段归一化，与本数据集字段一一对应。

---

## 许可

MIT。数据本身来自公开政策文件；整理工作与字段设计以 MIT 授权，使用请保留出处。
