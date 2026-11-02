# Changelog

本文件记录电价数据的变更。字段结构变更与数据变更分开记。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

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
