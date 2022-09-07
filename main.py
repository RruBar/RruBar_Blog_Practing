from flask import Flask, render_template, redirect, url_for, flash,abort
from functools import wraps
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manger = LoginManager()
login_manger.init_app(app)

@login_manger.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

##CONFIGURE TABLES

class User(UserMixin,db.Model):
    __tablename__="users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250),nullable=False)
    email = db.Column(db.String(250),unique=True,nullable=False)
    password = db.Column(db.String(250),nullable=False)
    #This will act like a List of BlogPost objects attached to each User.
    #The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost",back_populates="author")
    comments = relationship("Comment",back_populates='comment_author')


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    # 透過__tablename__來進行該表命名
    id = db.Column(db.Integer, primary_key=True)
    #Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id=db.Column(db.Integer, db.ForeignKey('users.id'))
    #Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment",back_populates='parent_post')

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post=relationship("BlogPost",back_populates="comments")
    text=db.Column(db.Text, nullable=False)
db.create_all()


def admin_only(fun):
    @wraps(fun)
    def decorated_fun(*args, **kwargs):
        # 如果使用者ID不等於1，顯示403error
        if current_user.id !=1:
            return abort(403)
        return fun(*args, **kwargs)
    return decorated_fun


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts,current_user=current_user)


@app.route('/register',methods=["POST","GET"])
def register():
    register_form=RegisterForm()
    if register_form.validate_on_submit():
        email=register_form.email.data
        user_data = User.query.filter_by(email=email).first()
        if user_data:
            flash("這個信箱已經註冊過了，你要不要登入看看?")
            return redirect(url_for('login'))
        else:
            hash_password=generate_password_hash(register_form.password.data,method='pbkdf2:sha256',salt_length=8)
            new_user=User(name=register_form.name.data,
                          email=register_form.email.data,
                          password=hash_password)
            # 在召喚新物件時，已經選定好class(db.table)了
            db.session.add(new_user)
            db.session.commit()

            # 註冊即完成認證
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html",form=register_form,current_user=current_user)


@app.route('/login',methods=["POST","GET"])
def login():
    loginform=LoginForm()
    if loginform.validate_on_submit():
        email=loginform.email.data
        user_data=User.query.filter_by(email=email).first()
        if not user_data:
            flash("查無此信箱(帳號)")
            return redirect(url_for('login'))
        elif not check_password_hash(user_data.password,loginform.password.data):
            flash("密碼錯誤")
            return redirect(url_for('login'))
        else:
            login_user(user_data)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html",form=loginform,current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


gravatar = Gravatar(app,size=100, rating='g', default='retro', force_default=False, force_lower=False)

@app.route("/post/<int:post_id>",methods=["GET","POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form=CommentForm()
    comment_content=form.body.data
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("您尚未註冊or登入")
            return  redirect(url_for('login'))
        new_comment = Comment(text=comment_content, comment_author=current_user, parent_post=requested_post)
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post,current_user=current_user,form=form)






@app.route("/about")
def about():
    return render_template("about.html",current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html",current_user=current_user)


@app.route("/new-post",methods=["POST","GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,current_user=current_user)


@app.route("/edit-post/<int:post_id>",methods=["POST","GET"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form,current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
