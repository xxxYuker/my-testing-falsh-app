import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# 配置数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'wo-de-mima-shi-shen-me' # 必须有密钥才能用 Session

db = SQLAlchemy(app)

# 初始化登录管理
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
    # 关联 User 表的 id
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # 让我们可以用 message.author 拿到对应的 User 对象
    author = db.relationship('User', backref='messages')

# ================= 路由逻辑 =================

@app.route("/", methods=['GET', 'POST'])
def home():
    # 处理发帖逻辑
    if request.method == 'POST':
        # 如果没登录就想发帖，甚至不会显示提交按钮，但为了安全再防一手
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        content = request.form.get('content')
        # 创建留言时，自动填入当前登录用户的 id
        new_msg = Message(content=content, author=current_user)
        
        db.session.add(new_msg)
        db.session.commit()
        return redirect("/")

    all_messages = Message.query.all()
    return render_template("index.html", messages=all_messages)

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

# --- 新增：登录路由 ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 1. 找人：去数据库查有没有这个名字
        user = User.query.filter_by(username=username).first()
        
        # 2. 验密：如果人存在，且密码对得上
        if user and user.check_password(password):
            login_user(user) # 发放通行证
            return redirect(url_for('home'))
        
        # 3. 失败：报错
        flash('账号或密码错误，请重试。')

    return render_template('login.html')

# --- 新增：登出路由 ---
@app.route('/logout')
@login_required # 只有登录的人才能访问这个路由
def logout():
    logout_user() # 收回通行证
    return redirect(url_for('home'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)