from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from xai_sdk import Client
from xai_sdk.chat import user, system  # ✅ 1. 这里引入了 system (你之前做对了)
from xai_sdk.tools import web_search, x_search
import os

# ================= 配置区域 =================
XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
MY_ACCESS_TOKEN = os.getenv("MY_ACCESS_TOKEN", "").strip()

if not XAI_API_KEY:
    print("⚠️ 警告: 未检测到 XAI_API_KEY，服务可能无法正常工作！")
# ===========================================

app = FastAPI()

# ✅ 2. 修改这里：增加 system_prompt 字段
class SearchRequest(BaseModel):
    query: str
    # 默认人设，如果 n8n 不传这个参数，就用下面这句话
    system_prompt: str = "你是一个有用的AI助手。" 

@app.post("/search")
async def search_grok(
    request: SearchRequest, 
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
    print(f"🤖 当前人设: {request.system_prompt}") # 打印一下方便调试
    
    try:
        client = Client(api_key=XAI_API_KEY)
        chat = client.chat.create(
            model="grok-4", # 建议确认一下模型名称，有时是 grok-beta 或 grok-2
            tools=[web_search(), x_search()],
        )
        
        # ✅ 3. 修改这里：把 system_prompt 塞给 AI
        if request.system_prompt:
            chat.append(system(request.system_prompt))
            
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
