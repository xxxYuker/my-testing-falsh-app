import requests
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify # <--- 注意这里加了 jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# 配置数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'wo-de-mima-shi-shen-me'

db = SQLAlchemy(app)

# 登录管理
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= 数据模型 =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref='messages')

# ================= 路由逻辑 =================

@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        content = request.form.get('content')
        new_msg = Message(content=content, author=current_user)
        db.session.add(new_msg)
        db.session.commit()
        return redirect("/")

    all_messages = Message.query.all()
    return render_template("index.html", messages=all_messages)

# --- 登录/注册/注销 (保持不变) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        flash('账号或密码错误')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# ================= 🆕 新增：API 接口 (给 Postman/机器人用的) =================
# 修改 api_post_message 函数，替换原来的

@app.route('/api/post_message', methods=['POST'])
def api_post_message():
    # --- 🔒 第一关：检查暗号 ---
    # 我们规定：请求头里必须带一个叫 'Authorization' 的字段
    # 它的值必须是 'my-secret-token-123' (你自己随便定)
    token = request.headers.get('Authorization')
    
    if token != 'my-secret-token-123333':
        # 如果暗号不对，直接返回 403 (禁止访问)
        return jsonify({"status": "error", "message": "你是谁？暗号不对！"}), 403

    # --- 第二关：正常处理数据 (和之前一样) ---
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "没收到数据"}), 400

    username = data.get('username', 'Bot')
    content = data.get('content')

    if not content:
        return jsonify({"status": "error", "message": "内容不能为空"}), 400

    bot_user = User.query.filter_by(username=username).first()
    if not bot_user:
        bot_user = User(username=username)
        bot_user.set_password('123456')
        db.session.add(bot_user)
        db.session.commit()

    new_msg = Message(content=content, author=bot_user)
    db.session.add(new_msg)
    db.session.commit()

    return jsonify({"status": "success", "message": "API留言成功"}), 201

# ...

@app.route('/n8n-tools')
@login_required  # 只有登录了才能进工坊
def n8n_tools():
    return render_template('n8n_tools.html')

@app.route('/generate_report', methods=['POST'])
@login_required
def generate_report():
    work_items = request.form.get('work_items')
    
    payload = {
        "user": current_user.username,
        "raw_text": work_items
    }
    
    n8n_url = "https://n8n.xdoworking.com/webhook/AI-Report"
    
    try:
        response = requests.post(n8n_url, json=payload, timeout=30)
        
        if response.ok:
            return render_template('n8n_tools.html', report_content=response.text)
        else:
            error_msg = f"❌ N8N 报错 (代码 {response.status_code}): {response.text}"
            print(error_msg, flush=True)
            flash(error_msg)
            
    except Exception as e:
        flash(f"❌ 出错: {str(e)}")

    return redirect(url_for('n8n_tools'))


@app.route('/generate_twitter', methods=['POST'])
@login_required
def generate_twitter():
    project_name = request.form.get('project_name')
    user_request = request.form.get('user_request')
    style = request.form.get('style')
    use_search = 'use_search' in request.form
    need_image = 'need_image' in request.form

    payload = {
        "user": current_user.username,
        "project_name": project_name,
        "user_request": user_request,
        "style": style,
        "use_search": use_search,
        "need_image": need_image,
    }

    n8n_url = "https://n8n.xdoworking.com/webhook/twitter-engine-v1"

    try:
        response = requests.post(n8n_url, json=payload, timeout=120)
        print(f"DEBUG状态码: {response.status_code}", flush=True)
        print(f"DEBUG内容: {response.text[:200]}", flush=True)

        if response.ok:
            try:
                twitter_result = response.json()
            except ValueError:
                twitter_result = response.text
            return render_template('n8n_tools.html', twitter_result=twitter_result)
        else:
            error_msg = f"❌ N8N 报错 (代码 {response.status_code}): {response.text}"
            print(error_msg, flush=True)
            flash(error_msg)

    except Exception as e:
        flash(f"❌ 出错: {str(e)}")

    return redirect(url_for('n8n_tools'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True) 
