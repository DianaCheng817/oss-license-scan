# src · MVP 原型源码 + 数据采集说明

本目录存放本项目数据的采集方式说明。

## 运行 MVP 原型

```
pip install -r requirements.txt
python main.py            # 监听 $PORT（默认 8000）
```

- `main.py`：FastAPI 全部接口（状态时间线/解释/异常分派/三口径/知识问答/事实台账）
- `static/index.html`：前端单页（包裹状态·三口径对照·知识问答·事实台账四个页签）
- `data/facts.json`：35 条访谈事实（与 `docs/02_调研记录.json` 同源）

**已部署线上**：https://returns-mvp.app.workbuddy.host/?sharecode=CRDF2OOZ6U （API 附加 `?sharecode=CRDF2OOZ6U`）

## 访谈数据采集

- **平台**：FDE 训练中心 · 3D 业务现场（`/api/group-lab/state`、`/api/group-lab/ask` 接口）
- **方式**：对 6 位角色（顾明岚、林亦舟、唐映秋、秦芮、傅景、叶书）按预设访谈话题逐题提问，每题记录问句、回答原文与新增事实编号，共 33 轮问答、35 条事实。
- **产出**：`../docs/02_调研记录.json`（结构化全量数据）、`02_调研记录.csv`（事实表）、`02_调研记录.md`（逐轮记录）。
- **采集会话**：`f9fec4b4-4a5b-49fb-8d57-09085c67f530`（独立练习会话，2026-11-05）。

采集脚本为临时脚本，运行后未归档；如需复现，按上述接口与参数（`scenarioId=ecommerce-returns`，`characterId` 见 json 中 `roles` 字段）重放即可。
