from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import web_search, x_search
import os

# ================= 配置区域 =================
# 1. xAI 的 Key (用于调用 AI)
token = os.getenv("XAI_API_KEY", "").strip()
# 2. 自定义的访问密码 (用于保护你的 API)
# 你可以随便设一个复杂的字符串，比如 "n8n-secret-password-2025"
MY_ACCESS_TOKEN = os.getenv("MY_ACCESS_TOKEN", "").strip()

if not token:
    print("⚠️ 警告: 未检测到 XAI_API_KEY，服务可能无法正常工作！")
# ===========================================

app = FastAPI()

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
async def search_grok(
    request: SearchRequest, 
    # 这里增加了一个参数，要求请求头里必须包含 x-token
    x_token: str = Header(None) 
):
    """
    接收 query 和 header token，验证通过后才调用 Grok
    """
    
    # --- 🔒 安全检查 ---
    if x_token != MY_ACCESS_TOKEN:
        print(f"⚠️ 警告：有人尝试非法访问！Token: {x_token}")
        raise HTTPException(status_code=401, detail="Invalid Access Token")
    # ------------------

    print(f"✅ 验证通过，收到请求: {request.query}")
    
    try:
        client = Client(api_key=XAI_API_KEY)
        chat = client.chat.create(
            model="grok-4",
            tools=[web_search(), x_search()],
        )
        chat.append(user(request.query))
        
        full_response = ""
        for response, chunk in chat.stream():
            if chunk.content:
                full_response += chunk.content
        
        return {
            "status": "success",
            "data": full_response
        }
        
    except Exception as e:
        print(f"出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
