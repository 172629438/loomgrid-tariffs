# Changelog

本文件记录电价数据的变更。字段结构变更与数据变更分开记。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [2026.06-rev2 · schema 2.0] — 2026-11-05

### Added
- **`market_regime` / `proxy_regime` / `market_source`**：区分「电网代理购电用户」与「市场化交易用户」两套定价机制。依据发改能源规〔2025〕1656号，自 2026-03-01 起入市用户不再人为规定分时电价。已取消固定分时电价的 9 地（贵州、河北南网、湖北、陕西、吉林、云南、重庆、辽宁、河南）标为 `market`，江苏/山西为 `pending`，其余 21 省 `unknown`（未核实）。
- **`price_zone` / `grid_company`**：价区与电网归属。河北按电网拆为 `冀北` 与 `河北南网` 两行；广东标注为四价区省份（珠三角六市/惠州/东西两翼/粤北）。
- **`price_sharp_peak_cny_per_kwh` / `price_deep_valley_cny_per_kwh`**：尖峰/深谷价格列（结构就位，数值待取）。
- **`period_type` 新增 `sharp_peak` / `deep_valley`**：尖峰不再沉在 `peak` 里。安徽（7-8月 20-22）、河南（1/12月 17-19、7-8月 20-23）、四川（7-8月 13-14、21-23）已完成结构化，共 5 条尖峰记录。
- **`source_url` / `verify_status` / `effective_to` / `voltage_level`**：来源链接、核实状态、失效日期、电压等级。
- **`scripts/check_proxy_price.py`**：月度代理购电巡检，快照 vs 库内 → 差异报告（含 `--demo` 自测）。
- **`scripts/price_snapshot_template.csv`**：巡检快照填写模板。
- **`meta.json` 新增 `needs_review`**：把未完成项写进数据文件，不再只靠口头交代。

### Changed
- 时段表行数 309 → 336（尖峰拆分所致）；省份 32 → 33（河北拆分）。
- `validate.py` 适配 v2：允许价格占位行与无时段省份，但要求显式声明 `verify_status`；新增 `market_regime` / `verify_status` 词表校验；“`market` 却无 `source_url`”记警告。
- README 字段表、数据边界、月度巡检章节同步重写。

### Known gaps（详见 `meta.json` 的 `needs_review`）
- 31 省 `effective_from` 仍为空。
- 广东四价区未拆行，分区价格未入库。
- 河北南网价格与时段为空值行。
- 上海、北京、天津、海南、福建、青海尖峰无明确月份/时段，未入库。
- 湖南 `source_note` 称 7-9 月尖峰 20-24，与时段表 22-24 为 flat 相矛盾，待核。
- 全库 `voltage_level` 为空；价格数值仍为 2026-06 版本，未做 7-11 月跟踪。

---

## [2026.06-rev1] — 2026-11-02

### Fixed
- **安徽时段重复**：春秋季与冬季的分段表里，`(23,24,'valley')` 与跨午夜段
  `(23,6,'valley')` 在 23 时重叠，导致该小时被计入两次。在 LoomGrid 主程序里
  这会生成两个重复的充电段（充电3 / 充电4 起点终点完全相同），使充电空间
  被高估一小时。已删除重复段。
- 时段记录数 311 → 309。价格字段未变。

### Added
- `validate.py`：数据集自检（年份集合一致 / 价格单调 / 24 小时无缝覆盖 /
  时长求和 / 类型词表）。**这个脚本就是发现上述缺陷的工具。**
- CI（`.github/workflows/validate.yml`）：每次改动自动跑 validate。
- issue 模板 `data_correction.yml`：强制要求政策文号，否则不予处理。

---

## [2026.06] — 2026-06-30

首个公开发布版本。

### Added
- 32 个省级行政区峰平谷电价、需量电费、推荐充放模式
- 311 条分季节时段记录（`province_tariff_periods.csv`）
- 完整嵌套 JSON 结构（`province_tariff.json`）
- 5 省需求响应补贴标准（广东 / 江苏 / 浙江 / 山东 / 上海）
- 每省 `source_note` 政策文号出处字段
- `CITATION.cff` 引用元数据

### Known gaps
- 价格为单一电压等级参考值，非分电压等级目录电价
- 不含代理购电月度浮动因子
- 尖峰 / 深谷未单独列价
- 需求响应补贴仅收录 5 省

---

## 维护约定

每次数据更新须完成：

1. `province_tariff_summary.csv` — 价格、`source_note`、`effective_from`
2. `province_tariff_periods.csv` — 该省全部时段行
3. `province_tariff.json` — 与上面两者同步
4. `meta.json` — 推进 `price_version`，更新省份清单（如有增减）
5. 本文件 — 记一笔「改了哪个省、依据哪份文件、改了什么」

数据版本命名：`YYYY.MM`，取该批数据的最新政策生效月份。
