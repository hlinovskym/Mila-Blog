from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,  RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import os
# from dotenv import load_dotenv

app = Flask(__name__)
app.app_context().push()

# SECRET_KEY right here
# app.config['SECRET_KEY'] = "look_in_69"

# SECRET_KEY stored in .env file
# load_dotenv("C:/Users/pocitac/PycharmProjects/EnvironmentVariables/.env")
# app.config['SECRET_KEY'] = os.getenv("APP_SECRET_KEY")

# SECRET_KEY stored in Environment at render.com
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")


ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
# local DB - SQLite
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
# remote db - PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

# CONFIGURE TABLES

# Create the User Table
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")

    # The "comments" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


# Create the Posts Table
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # ***************Child Relationship*************#
    # Create Foreign Key, "user.id" the user refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    # The "comments" refers to the comment_post property in the Comment class.
    comments = relationship("Comment", back_populates="parent_post")


# Create the User Table
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # ***************Child Relationship*************#
    # Create Foreign Key, "user.id" the user refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # Create reference to the User object, the "comments" refers to the comments property in the User class.
    comment_author = relationship("User", back_populates="comments")

    # Create Foreign Key, "user.id" the user refers to the tablename of User.
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    # Create reference to the User object, the "comments" refers to the comments property in the User class.
    parent_post = relationship("BlogPost", back_populates="comments")


# Create all the tables in the database
# Line below only required once, when creating DB.
db.create_all()

# flask login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if current_user.is_anonymous or current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


# Register new users into the User database
@app.route('/register',  methods=["GET", "POST"])
def register():
    new_user_form = RegisterForm()
    if new_user_form.validate_on_submit():
        # If user's email already exists
        if User.query.filter_by(email=request.form["email"]).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(
            request.form["password"],
            method="pbkdf2:sha256",
            salt_length=8
        )
        new_user = User(
            name=request.form["name"],
            email=request.form["email"],
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=new_user_form, current_user=current_user)


@app.route('/login',  methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = request.form["email"]

        # find user by email
        user = User.query.filter_by(email=email).first()
        #  if user doesn't exist
        if not user:
            flash("User doesn't exist!")
            return redirect(url_for('login'))
        # check stored password hash against entered password hash
        elif not check_password_hash(user.password, request.form["password"]):
            flash('Wrong password!')
            return redirect(url_for('login'))
        # everything alright
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",  methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()

    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=form.comment_text.data,
                comment_author=current_user,
                parent_post=requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
            # return redirect(url_for('get_all_posts'))
        else:
            flash('Log In First!')
            return redirect(url_for('login'))
    return render_template("post.html", post=requested_post, current_user=current_user, form=form)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)


@app.route("/new-post",  methods=["GET", "POST"])
@admin_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>",  methods=["GET", "POST"])
@admin_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author_id.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_required
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5000)
if __name__ == '__main__':
    app.run(debug=False)
