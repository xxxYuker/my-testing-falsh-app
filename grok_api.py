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
    # --- 🔒 安全检查 ---
    if x_token != MY_ACCESS_TOKEN:
        print(f"⚠️ 警告：有人尝试非法访问！Token: {x_token}")
        raise HTTPException(status_code=401, detail="Invalid Access Token")
    # ------------------

    print(f"✅ 验证通过，收到请求: {request.query}")
    print(f"🤖 当前 system_prompt: {request.system_prompt}")

    try:
        client = Client(api_key=XAI_API_KEY)

        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[web_search(), x_search()],
            include=["verbose_streaming"],  # ✅ 关键：更清晰的工具调用流信息
        )

        if request.system_prompt:
            chat.append(system(request.system_prompt))

        chat.append(user(request.query))

        full_response = ""
        final_response = None

        for response, chunk in chat.stream():
            final_response = response  # ✅ 记录最终 response（用于 citations/tool_calls）

            # ✅ 关键：实时打印工具调用（你用它判断“到底有没有搜”）
            tool_calls = getattr(chunk, "tool_calls", None) or []
            for tc in tool_calls:
                try:
                    fn = tc.function.name
                    args = tc.function.arguments
                    print(f"\n🔧 TOOL CALL => {fn} args={args}")
                except Exception:
                    print(f"\n🔧 TOOL CALL => {tc}")

            # 收集最终文本
            if getattr(chunk, "content", None):
                full_response += chunk.content

        # ✅ citations 默认就会返回（文档：response.citations always returned）
        citations = safe_serialize(getattr(final_response, "citations", []))
        server_side_tool_usage = safe_serialize(getattr(final_response, "server_side_tool_usage", None))
        tool_calls_summary = safe_serialize(getattr(final_response, "tool_calls", None))

        return {
            "status": "success",
            "data": full_response,
            "citations": citations,
            "server_side_tool_usage": server_side_tool_usage,
            "tool_calls": tool_calls_summary,
        }

    except Exception as e:
        print(f"出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
