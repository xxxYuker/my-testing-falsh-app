from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search, x_search
import os
from typing import Any
import logging, time, uuid
log = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)

# ================= 配置区域 =================
XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
MY_ACCESS_TOKEN = os.getenv("MY_ACCESS_TOKEN", "").strip()

if not XAI_API_KEY:
    print("⚠️ 警告: 未检测到 XAI_API_KEY，服务可能无法正常工作！")
# ===========================================

app = FastAPI()


class SearchRequest(BaseModel):
    query: str
    system_prompt: str = "你是一个有用的AI助手。"


def safe_serialize(obj: Any):
    """
    把 SDK 对象尽量变成可 JSON 序列化的形态，避免 FastAPI 返回时报错。
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [safe_serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: safe_serialize(v) for k, v in obj.items()}
    # protobuf / pydantic / 自定义对象兜底
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return str(obj)


@app.post("/search")
async def search_grok(request: SearchRequest, x_token: str = Header(None)):
    rid = str(uuid.uuid4())
    t0 = time.time()
    log.info(f"[{rid}] /search start query={request.query!r}")

    try:
        client = Client(api_key=XAI_API_KEY)

        log.info(f"[{rid}] TOOL grok_chat.create start tools=[web_search,x_search]")
        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[web_search(), x_search()],
            include=["verbose_streaming", "inline_citations"],
        )
        log.info(f"[{rid}] TOOL grok_chat.create end cost_ms={(time.time()-t0)*1000:.1f}")

        if request.system_prompt:
            chat.append(system(request.system_prompt))

        chat.append(user(request.query))

        full_response = ""
        final_response = None
        triggered_tools = []

        # 注意：这里的工具调用是“流式过程中的事件”，不代表一定每次都会触发
        for response, chunk in chat.stream():
            final_response = response

            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                for tc in chunk.tool_calls:
                    tool_name = tc.function.name
                    tool_args = tc.function.arguments
                    log.info(f"[{rid}] TOOL_CALL {tool_name} args={tool_args}")
                    triggered_tools.append({"name": tool_name, "args": tool_args})

            if getattr(chunk, "content", None):
                full_response += chunk.content

        citations = safe_serialize(getattr(final_response, "citations", []))
        server_side_usage = safe_serialize(getattr(final_response, "server_side_tool_usage", None))

        log.info(f"[{rid}] /search end cost_ms={(time.time()-t0)*1000:.1f} "
                 f"server_side_tool_usage={server_side_usage}")

        return {
            "status": "success",
            "data": full_response,
            "citations": citations,
            "server_side_tool_usage": server_side_usage,
            "debug_triggered_tools": triggered_tools,
            "rid": rid,
        }

    except Exception as e:
        log.exception(f"[{rid}] /search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
