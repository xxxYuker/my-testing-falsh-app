from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search, x_search
import os
from typing import Any

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
    # ... (前面的安全检查保持不变) ...

    print(f"✅ 收到请求: {request.query}")

    try:
        client = Client(api_key=XAI_API_KEY)

        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[web_search(), x_search()],
            # ✅ 修正点 1: 添加 inline_citations 以获得可见的引用标记
            include=["verbose_streaming", "inline_citations"],
        )

        if request.system_prompt:
            chat.append(system(request.system_prompt))

        chat.append(user(request.query))

        full_response = ""
        final_response = None
        
        # 用于在控制台调试是否真的触发了工具
        triggered_tools = []

        for response, chunk in chat.stream():
            final_response = response
            
            # ✅ 修正点 2: 增强的工具检测逻辑
            # 在 verbose_streaming 模式下，工具调用会出现在 chunk.tool_calls 中
            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                for tc in chunk.tool_calls:
                    tool_name = tc.function.name
                    tool_args = tc.function.arguments
                    print(f"🔥 实时监测到工具调用: {tool_name} | 参数: {tool_args}")
                    triggered_tools.append({"name": tool_name, "args": tool_args})

            if chunk.content:
                full_response += chunk.content

        # 最终的数据提取
        citations = safe_serialize(getattr(final_response, "citations", []))
        # ✅ 修正点 3: server_side_tool_usage 是判断是否搜索的最权威证据
        server_side_usage = safe_serialize(getattr(final_response, "server_side_tool_usage", None))
        
        print(f"📊 最终服务端工具统计: {server_side_usage}")

        return {
            "status": "success",
            "data": full_response,
            "citations": citations,
            "server_side_tool_usage": server_side_usage, # 如果这里有值，说明绝对搜索了
            "debug_triggered_tools": triggered_tools     # 实时捕获的工具列表
        }

    except Exception as e:
        print(f"出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
