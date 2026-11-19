"""万象优选 · 退货验收与售后协同 — MVP 原型（训练数据）"""
import json, os, re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
FACTS = json.load(open(BASE / "data" / "facts.json", encoding="utf-8"))
FACT_LIST = FACTS["facts"]
FACT_BY_ID = {f["id"]: f for f in FACT_LIST}

# 演示包裹数据（训练场景合成数据，节点时间戳为示意）
PARCELS = {
    "WB2026W44-001": {
        "parcel_id": "WB2026W44-001", "after_sale_ids": ["AS-88621"],
        "current_node": "queued_not_visible",
        "timeline": [
            {"node": "客户提交退货申请", "actor": "客服", "at": "2026-11-02 09:14", "status": "done"},
            {"node": "订单与政策校核", "actor": "客服/工单员", "at": "2026-11-02 09:40", "status": "done"},
            {"node": "客户寄回", "actor": "客户", "at": "2026-11-02 15:22", "status": "done"},
            {"node": "仓库签收", "actor": "收货岗", "at": "2026-11-03 08:05", "status": "done"},
            {"node": "待质检排队", "actor": "待定", "at": None,
             "status": "black_box",
             "note": "签收→排检无系统状态、无标准时限（f10），责任岗位待定"},
            {"node": "开箱与质检判定", "actor": "质检员", "at": None, "status": "pending"},
            {"node": "退款审批", "actor": "审批人", "at": None, "status": "pending"},
        ],
    },
    "WB2026W44-002": {
        "parcel_id": "WB2026W44-002", "after_sale_ids": ["AS-88714"],
        "current_node": "refund_pending",
        "timeline": [
            {"node": "客户提交退货申请", "actor": "客服", "at": "2026-11-01 10:02", "status": "done"},
            {"node": "仓库签收", "actor": "收货岗", "at": "2026-11-02 09:30", "status": "done"},
            {"node": "质检判定 PASS", "actor": "质检员", "at": "2026-11-02 14:10", "status": "done"},
            {"node": "退款审批", "actor": "审批人", "at": None,
             "status": "in_progress", "note": "按金额分级签核（f41）"},
        ],
    },
    "WB2026W44-003": {
        "parcel_id": "WB2026W44-003", "after_sale_ids": ["AS-88690", "AS-88691"],
        "current_node": "exception_hold",
        "timeline": [
            {"node": "仓库签收", "actor": "收货岗", "at": "2026-11-03 10:47", "status": "done"},
            {"node": "异常暂停：一包多单", "actor": "质检员", "at": "2026-11-03 11:02",
             "status": "exception",
             "note": "包裹含 2 个订单、退回件数与申请不符，暂停判定待工单员核对（f11、f15）"},
        ],
        "exception": {"type": "一包多单/数量不符", "assignee": "工单员",
                      "checklist": ["核对包裹内订单清单", "逐单核对退回件数", "结论写明核对依据"],
                      "closed": False},
    },
}

# 三口径完成量（f53，训练合成数据）
CALIBER = {"cs": {"name": "客服·到仓", "count": 10500},
           "wh": {"name": "仓库·验收", "count": 9847},
           "fin": {"name": "财务·到账", "count": 9402}}

app = FastAPI(title="退货验收与售后协同 MVP", version="0.1.0",
              description="训练场景原型：签收后状态可视化 / 异常件提示 / 三口径对账 / 事实知识问答。数据为训练合成事实。")

@app.get("/api/parcels/{parcel_id}/status")
def parcel_status(parcel_id: str):
    p = PARCELS.get(parcel_id)
    if not p:
        raise HTTPException(404, "包裹不存在（演示数据仅 WB2026W44-001/002/003）")
    out = {k: p[k] for k in ("parcel_id", "after_sale_ids", "current_node", "timeline")}
    if p["current_node"] == "queued_not_visible":
        out["waiting_reason"] = "queued_not_visible"  # f10 空窗
    return out

@app.get("/api/parcels/{parcel_id}/explain")
def parcel_explain(parcel_id: str):
    p = PARCELS.get(parcel_id)
    if not p:
        raise HTTPException(404, "包裹不存在")
    node = p["current_node"]
    if node == "queued_not_visible":
        text = "仓库已签收，但尚未排上质检：签收后到排检之间没有系统状态，也无法给出预计时间（依据 f10）。"
        cites = ["f10", "f12"]
    elif node == "exception_hold":
        text = "包裹为一包多单且退回件数与申请不符，已暂停判定，待工单员拆单核对；核对完成前不进入质检（依据 f11、f15）。"
        cites = ["f11", "f15", "f25"]
    elif node == "refund_pending":
        text = "质检判定已通过，正在退款审批；审批按金额分级签核，AI 不代替审批人做决定（依据 f41）。"
        cites = ["f41", "f44"]
    else:
        text = "当前节点正常流转。"
        cites = []
    return {"parcel_id": parcel_id, "explanation": text, "citations": cites}

@app.post("/api/exceptions/{parcel_id}/claim")
def claim_exception(parcel_id: str):
    p = PARCELS.get(parcel_id)
    if not p or "exception" not in p:
        raise HTTPException(404, "该包裹无异常待办")
    p["exception"]["closed"] = False
    return {"assignee": p["exception"]["assignee"], "checklist": p["exception"]["checklist"],
            "sla_hint": None,  # 异常件停留时长尚无统计，不编造（f11）
            "note": "待办以接手人确认为完成，不自动关闭（f23）"}

@app.get("/api/metrics/completion")
def completion(date: str = "2026-W44"):
    vals = {k: v["count"] for k, v in CALIBER.items()}
    diff = max(vals.values()) - min(vals.values())
    return {"date": date, "calibers": CALIBER, "max_diff": diff,
            "diff_percent": round(diff / max(vals.values()) * 100, 1),
            "source": "f53", "note": "三套完成口径互不一致，口径统一是收益可度量的前置（O3）"}

SYNONYMS = {
    "一包多单": ["多个订单", "件数量", "不一致"], "卡在哪": ["签收", "排", "等待"],
    "黑箱": ["签收", "排", "状态"], "多久": ["天", "分钟", "时长"], "红线": ["不能", "权限", "退款"],
    "异常件": ["异常", "不一致", "分派"], "完成": ["到仓", "验收", "到账"], "口径": ["到仓", "验收", "到账"],
}

def bigrams(s: str):
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}

@app.get("/api/kb/ask")
def kb_ask(q: str):
    terms = [t for t in re.split(r"[\s，。？、,?]+", q) if t]
    expanded = []
    for t in terms:
        expanded.append(t)
        for k, vs in SYNONYMS.items():
            if k in t:
                expanded.extend(vs)
    expanded = list(dict.fromkeys(expanded))
    scored = []
    for f in FACT_LIST:
        blob = f["text"] + f["topic"] + f["role"] + f["evidence"]
        fb = bigrams(blob)
        s = 0
        for t in expanded:
            if t in blob:
                s += 3
            s += 0.3 * len(bigrams(t) & fb)
        if s > 1:
            scored.append((s, f))
    scored.sort(key=lambda x: -x[0])
    hits = [{"fact_id": f["id"].replace("ecommerce-returns-", ""), "text": f["text"],
             "role": f["role"], "evidence": f["evidence"]} for _, f in scored[:3]]
    if not hits:
        return {"answer": "尚无记录。", "citations": [],
                "note": "无来源不编造（f34 口径）"}
    return {"answer": "按知识库检索到的相关记录：", "citations": hits}

@app.get("/api/facts")
def facts():
    return [{"fact_id": f["id"].replace("ecommerce-returns-", ""), "text": f["text"],
             "character": f["character"], "role": f["role"], "topic": f["topic"]}
            for f in FACT_LIST]

@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")

app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
