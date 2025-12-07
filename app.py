import os
from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ================= 1. 数据库配置 =================
# 告诉 Flask，数据库文件叫 data.db，就放在当前文件夹里
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.db')
# 关闭一个不必要的警告
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库管理器
db = SQLAlchemy(app)

# ================= 2. 定义数据模型 (像设计 Excel 表头) =================
# 我们创建一个叫 Message 的类，代表一条留言
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # 每一行都有个唯一的编号
    name = db.Column(db.String(50))               # 姓名列，最长50个字
    content = db.Column(db.String(200))           # 内容列，最长200个字

# ================= 3. 自动创建数据库文件 =================
# 这一步非常重要：程序启动时，如果发现没有数据库，就自动建一个
with app.app_context():
    db.create_all()

# ================= 4. 路由逻辑 =================
# methods=['GET', 'POST'] 意思是：这个网页既可以看(GET)，也可以提交数据(POST)
@app.route("/", methods=['GET', 'POST'])
def home():
    # 如果用户点击了“提交”按钮 (POST请求)
    if request.method == 'POST':
        # 1. 从网页表单里拿到数据
        username = request.form.get('name')
        message_content = request.form.get('content')
        
        # 2. 创建一条新留言记录 (Python 对象)
        new_msg = Message(name=username, content=message_content)
        
        # 3. 让数据库保存 (相当于点了 Excel 的保存按钮)
        db.session.add(new_msg)
        db.session.commit()
        
        # 4. 刷新页面，避免重复提交
        return redirect("/")

    # 如果是普通访问 (GET)，就去数据库里把所有留言都取出来
    # Message.query.all() 相当于 "SELECT * FROM message"
    all_messages = Message.query.all()
    
    # 把取出的列表传给网页显示
    return render_template("index.html", messages=all_messages)

if __name__ == "__main__":
    app.run(debug=True)