# 中国省级分时电价数据集 · China Provincial TOU Tariff Dataset

**33 个电网价区 · 覆盖 31 个省级行政区 · 峰平谷电价 · 分季节时段表 · 需求响应补贴**
**33 grid pricing zones across 31 provincial-level regions · peak/flat/valley prices · seasonal period tables · demand-response subsidies**

[![Zones](https://img.shields.io/badge/pricing_zones-33-2f6b4f?style=flat-square)](#覆盖范围)
[![Regions](https://img.shields.io/badge/provincial_regions-31-2f6b4f?style=flat-square)](#覆盖范围)
[![Periods](https://img.shields.io/badge/period_records-577-2f6b4f?style=flat-square)](#文件结构)
[![validate](https://github.com/172629438/loomgrid-tariffs/actions/workflows/validate.yml/badge.svg)](https://github.com/172629438/loomgrid-tariffs/actions/workflows/validate.yml)
[![Price version](https://img.shields.io/badge/price_version-2026--06-9a7b2e?style=flat-square)](#数据版本与时效)
[![License](https://img.shields.io/badge/license-MIT-2f6b4f?style=flat-square)](LICENSE)

> 一份可以直接 `read_csv` 拿来算储能、光伏、需量管理的中国分时电价表。
> 每个省都带**政策文号出处**——这是它和网上转载版本最大的区别。
>
> A machine-readable dataset of China's time-of-use (TOU) electricity tariffs, with **policy document citations** for every province.

---

## English summary

China's industrial & commercial (C&I) electricity tariffs are **time-of-use based**: each day is split into peak / flat / valley segments, and every province defines its own segment boundaries, its own seasonal groupings, and its own price levels. There is no single national file — practitioners rebuild this table from provincial NDRC notices, by hand, for every project.

This dataset collects the result of that work for **33 grid pricing zones across 31 provincial-level regions**, as of **price version 2026-06**:

- `data/province_tariff_summary.csv` — one row per region: peak/flat/valley price, demand charge, charging-cycle mode, policy citation
- `data/province_tariff_periods.csv` — long format: region × season × time segment (577 records)
- `data/province_tariff.json` — full nested structure, drop-in for application code
- `data/dr_subsidy.csv` — demand-response subsidy standards (5 regions with published rates)

Built and maintained by the author of [LoomGrid](https://github.com/172629438/loomgrid), a C&I BESS sizing studio, because this table gets rebuilt from scratch on every project.

**Read the caveats in [数据边界](#数据边界) before using it for anything contractual.**

---

## 覆盖范围

**33 个电网价区**，覆盖 31 个省级行政区。河北拆为冀北与河北南网、内蒙古拆为蒙东与蒙西——两边电价与时段都不相同，合成一省就失真了。

> 其中**河北南网为结构占位**：电网归属、政策机制与生效年月已登记，但价格与时段未取，是空值行。实际可直接用于测算的是 32 个价区。判据不靠记文档——每行的 `period_table_status` 字段写着它能不能用。

按电网区域划分：

| 区域 | 电网价区 |
|---|---|
| 华东 | 上海 · 江苏 · 浙江 · 安徽 · 福建 · 江西 · 山东 |
| 华南 | 广东 · 广西 · 海南 |
| 华中 | 河南 · 湖北 · 湖南 |
| 华北 | 北京 · 天津 · 冀北 · 河北南网 · 山西 · 蒙东 · 蒙西 |
| 西北 | 陕西 · 甘肃 · 青海 · 宁夏 · 新疆 |
| 西南 | 四川 · 重庆 · 云南 · 贵州 · 西藏 |
| 东北 | 辽宁 · 吉林 · 黑龙江 |

> 早先版本把这表写成 32 项，是因为河北只列了“河北”一条；实际上冀北与河北南网分属不同价区，是两条记录。

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
├── province_tariff_summary.csv    33 行 · 一省一行 · 价格/需量/机制/价区/出处
├── province_tariff_periods.csv   577 行 · 省份×季节×时段 长表（含尖峰/深谷）
├── province_tariff.json           完整嵌套结构（schema 2.0）
├── dr_subsidy.csv                  5 行 · 需求响应补贴
└── meta.json                      版本 / 省份清单 / 待补清单 needs_review
scripts/
├── check_proxy_price.py           月度代理购电巡检：快照 vs 库内 → 差异报告
└── price_snapshot_template.csv    巡检快照填写模板
```

### `province_tariff_summary.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| `province` | str | 省级行政区名（中文，如 `浙江`）；河北按电网拆为 `冀北` / `河北南网` |
| `price_peak_cny_per_kwh` | float \| blank | 高峰电价，元/kWh；空值=占位行，数值未取 |
| `price_flat_cny_per_kwh` | float \| blank | 平段电价，元/kWh |
| `price_valley_cny_per_kwh` | float \| blank | 低谷电价，元/kWh |
| `price_sharp_peak_cny_per_kwh` | float \| blank | 尖峰电价；空=该省未单列尖峰价或未取 |
| `price_deep_valley_cny_per_kwh` | float \| blank | 深谷电价；同上 |
| `demand_charge_cny_per_kva_month` | float | 需量（基本）电费，元/kVA·月 |
| `charging_mode` | str | 推荐充放模式：`一充一放` / `两充两放` / `现货市场` |
| `effective_from` | str \| blank | 政策生效日（`YYYY-MM-DD`），未知则留空 |
| `effective_to` | str \| blank | 政策失效日；空=现行 |
| `source_note` | str | **政策文号与要点**，如「浙发改价格〔2026〕112号(2026.7.1生效)」 |
| `seasonal_periods` | bool | 是否分季节定义时段（`yes`/`no`） |
| `price_zone` | str | 价区。`全省` 或具体分区；广东为四价区省份，本表保留一行全省参考值 |
| `grid_company` | str | 电网企业，如 `国网浙江` / `南网广东` / `内蒙古电力` |
| `proxy_regime` | str | **电网代理购电用户**的定价机制，多数为 `regulated` |
| `market_regime` | str | **市场化交易用户**的定价机制：全库均为 `market`，依据见下 |
| `market_source` | str | 上述判定的政策依据说明 |
| `voltage_level` | str \| blank | 电压等级；全库为空=未分档，见「数据边界」 |
| `source_url` | str \| blank | 官方来源链接 |
| `verify_status` | str | 核实状态：`none` / `policy`（政策已核、价未核）/ `price` / `full` |
| `period_table_status` | str | **时段表可信度**：`verified` / `partial` / `template_suspected` / `unverified`，见「时段表可信度」一节 |

> **`market_regime` 是 v2 最重要的新字段。** 2025 年 12 月《电力中长期市场基本规则》（发改能源规〔2025〕1656号）**第三十五条为全国性规定**：「对直接参与市场交易的经营主体，不再人为规定分时电价水平和时段；对电网代理购电用户，由政府价格主管部门……」自 2026-03-01 起对**全部省份**生效，不是各省自行选择。
>
> 因此全库 33 行的 `market_regime` 均为 `market`。差别只在 `market_source`：贵州、河北南网、湖北、陕西、吉林、云南、重庆、辽宁、河南等另发单独落地文件；其余省份直接适用国家规则，未见单独文件。
>
> 这意味着：**同一省的峰平谷表，仅对电网代理购电用户有效；市场化用户的价格由市场形成。** 拿这张表算市场化用户的储能收益，会按旧峰谷价差得出错误结论。

### `province_tariff_periods.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| `province` | str | 省级行政区名 |
| `season` | str | 季节标签，如 `2-11月等8个月` / `全年` |
| `months` | str | 该季节对应的月份，逗号分隔（`2,3,4,...`） |
| `start_hour` | int | 时段起点（0–24） |
| `end_hour` | int | 时段终点（0–24）；`end < start` 表示跨午夜 |
| `duration_h` | float | 时长（小时） |
| `period_type` | str | `peak` / `flat` / `valley` / `sharp_peak` / `deep_valley` |
| `source_basis` | str | 该行数据的依据说明（尖峰行记录其来自原 `source_note` 的哪句话） |

> 跨午夜提示：`(23, 6, 'valley')` 表示 23:00 至次日 06:00，`end_hour < start_hour`。
> `duration_h` 已按跨午夜修正。

> 尖峰/深谷已从备注提升为结构化时段类型（`sharp_peak` / `deep_valley`），不再沉在 `peak` 里。当前完成结构化的是安徽、河南、四川三地的尖峰，以及河北（冀北）的深谷；其余省份的尖峰由 `source_note` 文字描述，尚未入库，见 `meta.json` 的 `needs_review`。

---

## 数据版本与时效

| 项 | 值 |
|---|---|
| schema 版本 | `2.0` |
| 数据版本 | `2026-06`（价格数值未重新取价） |
| 生效日期覆盖 | 8 / 33（其余未检索到可确认的官方文件，留空不臆造） |
| 建议复核周期 | 6 个月 |
| 数据来源 | 各省发改委 / 能源局分时电价公告，人工整理 |

中国分时电价调整频繁——仅 2026 年上半年就有浙江、江苏、安徽、山东等多省调整峰谷时段或取消上午高峰。**任何超过 6 个月未复核的电价数据，都不应直接用于报价。**

本项目内置的 `meta.json` 里带 `price_version` 与 `check_months` 字段，应用层可据此做时效告警。

---

## 时段表可信度

**每行数据都带 `period_table_status` 字段，程序可直接读，不必靠人记得翻文档。**

| 取值 | 含义 | 省份数 |
|---|---|---|
| `verified` | 逐条对回官方文件并重写，带文号与来源链接 | 19 |
| `partial` | 仅尖峰段已核，峰/平/谷划分未复核 | 4 |
| `template_suspected` | 可证实为模板复制（与他省逐行相同）且未核 | 5 |
| `unverified` | 未对过任何官方文件 | 5 |

已核的 19 省：北京、上海、福建、山东、天津、山西、江西、黑龙江、辽宁、甘肃、新疆、广西、陕西、青海、蒙西、蒙东、浙江、江苏、冀北。

仅尖峰已核的 4 省：安徽、河南、四川、湖南。

仍疑模板复制的 5 省：海南、云南、贵州、宁夏、重庆。

### 为什么有 `template_suspected` 这一档

把 16 个单季省的时段表逐行比对后发现 5 组完全相同——不同省份、不同电网、不同资源禀赋，时段却一个格子不差。已核实的辽宁与黑龙江、甘肃与宁夏、新疆与青海、广西与海南原本都是这种「一对共用一张表」的关系，其中前四对已剥离，剩下三张都是未核。

这类表比「空值」更危险：它看着完整、能算、不会报错，但数字是拿别的省套的。所以单独列一档 `template_suspected`，而不是埋进 `unverified` 里。

> **用前判断：`period_table_status` 不是 `verified` 的，时段划分不要用于测算。** `partial` 的可用尖峰窗口，`template_suspected` 与 `unverified` 一律不可用。

---

## 数据边界

诚实交代这份数据**不覆盖**什么。做商务决策前请逐条确认。

1. **单一电压等级参考价。** `price_*` 是各省代表性的工商业电价水平，**不是**分电压等级（1–10kV / 35kV / 110kV）的完整目录电价。实际结算价按电压等级与用户类别不同，差异可达 10–20%。
2. **不含代理购电浮动。** 2023 年后多数省份工商业用户电价由「代理购电价格 + 输配电价 + 系统运行费 + 政府性基金」构成，且按月浮动。本数据集给出的是结构性参考值，不含月度浮动因子。
3. **尖峰与深谷分档已完成、价格未齐。** `period_type` 已支持 `sharp_peak` / `deep_valley`，但 `price_sharp_peak_cny_per_kwh` / `price_deep_valley_cny_per_kwh` 两列目前全空——时段结构先行，价格待取。结构化进度不均：安徽/河南/四川的尖峰、河北（冀北）的深谷已入库，上海、北京、天津、海南、福建、青海的尖峰因原备注未写明月份或时段而留在备注里。
4. **不含容量电价机制差异。** 需量电费按元/kVA·月给出统一参考值，实际按变压器容量计费与按最大需量计费的规则各省不同（如 114 号文相关条款）。
5. **市场化用户适用性已按国家规则统一建模。** 1656 号文第三十五条为全国性规定，故全部省份 `market_regime` 均为 `market`；`market_source` 区分「另有单独落地文件」与「直接适用国家规则」两种情形。
6. **河北南网为结构占位。** 该行已登记电网归属、政策机制与生效年月（2025-11），但价格与时段未取，为空值行。
7. **需求响应补贴仅 5 省。** 其余省份未收录（未收录 ≠ 无政策）。
8. **人工整理，可能有误。** 每一省都标注了出处，但整理过程难免出错。发现错误请开 issue，注明省份 + 政策文号 + 正确值。

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

## 自检

两个脚本，各管一层：

```bash
python validate.py              # 结构自洽：覆盖无洞、时长合计、价格单调、字段词表
python scripts/audit_hours.py   # 分布合理：单档超 14h、平段为 0、合计不等于 24 即告警
```

`validate.py` 保证表“自己说得通”，`audit_hours.py` 保证表“看着像真的”。两层都过，才敢拿去用。

`audit_hours.py` 当前检出的异常：

| 省 | 峰 | 平 | 谷 | 问题 |
|---|---|---|---|---|
| 宁夏 | 5 | 2 | 17 | 谷段 17h 过长 |
| 西藏 | 5 | 0 | 19 | 谷段 19h 过长、平段为 0 |

分时机制不会没有平段。这两条与它们的 `unverified` / `template_suspected` 标记互相印证。

数据集自带一个校验器，检查的不是「数据对不对」（那要人对照政策文件），
而是「数据自不自洽」——一份自相矛盾的表，无论拄得多认真都是错的。

```bash
python validate.py
```

不需要装任何依赖，只用标准库。退出码 0 = 全过。

六类检查：

| 检查 | 抓什么 |
|---|---|
| 省份集合一致 | summary.csv 与 json 的省份对不上 |
| 价格单调 | `peak > flat > valley` 被破坏 |
| 小时覆盖 | 某个小时没人认领，或两个时段同时占用 |
| 时长求和 | 一个季节组的时长加起来不是 24 h |
| duration_h 自洽 | 声明值与 `(end-start)%24` 对不上 |
| 类型词表 | 出现 `period_type` 未收录的词 |

**这个脚本是真的有用。** 它写出来当天就抓到了安徽两组季节时段重复、
合计 25 小时的问题——那段数据从主程序里原样搬过来，人工看了一个多月没人发现。
细节见 [CHANGELOG](CHANGELOG.md)。

CI 每次 push 都跑它（`.github/workflows/validate.yml`）。

推新的数据时先本地跑一遍再提交。

---

## 月度巡检（价格跟踪）

电价每月变，但“实时更新”在这个领域是个伪需求：代理购电价格按月发布，时段政策不定期发布；而电价错一毛钱，项目回收期能错半年。不能自动写库。

正确的形态是三步：**取数 → 确定性比对 → 人工确认发版**。本项目实现了后两步。

正确的形态是三步：**取数 → 确定性比对 → 人工确认发版**。本项目实现了后两步。

```bash
# 1. 从当月各地电网公告抄录快照（模板见 scripts/price_snapshot_template.csv）
# 2. 比对，产出差异报告
python scripts/check_proxy_price.py --snapshot snapshot-2026-11.csv --json

# 自测：造一份只把浙江高峰价改 +0.02 的快照，验证脚本能抓到
python scripts/check_proxy_price.py --demo
```

报告会列出：价格变动（旧值/新值/差额/方向）、快照中多出的省份或价区、价区口径不一致、快照未覆盖省份。退出码 `0` = 无差异，`1` = 有差异，可直接接 CI 报警。

为什么取数不自动化：各省公告分散在 31 个省级发改委和三十余家电网公司，HTML 页面、PDF 扫描件、公众号图文混着来，不少页面还是 JS 渲染（实测取不到表格数值）。全自动抓取做不到不丢不错，所以取数留给 adapter 接口与人工确认，脚本只负责保证“变了这件事每次都被看见”。

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
  note   = {33 grid pricing zones across 31 provincial-level regions, price version 2026-06},
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
