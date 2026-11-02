# Changelog

本文件记录电价数据的变更。字段结构变更与数据变更分开记。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

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
