from waitress import serve
from app import app  # 从 app.py 里把你的“餐厅”导入进来

print("由于 waitress 不会主动打印提示，所以我自己写一行：")
print("正式服务器正在运行中... 请访问 http://127.0.0.1:8080")

# 启动服务
# host='0.0.0.0' 意思是对所有人都开放（而不只是你自己）
# port=8080 是我们这次选用的“大门”（常用 8080 作为备选端口）
serve(app, host='0.0.0.0', port=8080)