# import os
# import sys
# import getpass
# from flask import Flask, render_template, redirect, url_for, request, flash
# from flask_sqlalchemy import SQLAlchemy
# from flask_admin import Admin, AdminIndexView, expose
# from flask_admin.contrib.sqla import ModelView
# from flask_admin.form import FileUploadField
# from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
# from werkzeug.security import generate_password_hash, check_password_hash
# from werkzeug.utils import secure_filename
# from markupsafe import Markup
# from flask_migrate import Migrate

# app = Flask(__name__)

# # Create instance folder if needed
# try:
#     os.makedirs(app.instance_path)
# except OSError:
#     pass

# db_path = os.path.join(app.instance_path, 'news.db')
# app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SECRET_KEY'] = 'this-should-be-a-secret-key'

# db = SQLAlchemy(app)
# migrate = Migrate(app, db)

# login_manager = LoginManager(app)
# login_manager.login_view = 'login'


# # Models

# class User(db.Model, UserMixin):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(150), unique=True, nullable=False)
#     password_hash = db.Column(db.String(256), nullable=False)

#     def set_password(self, password):
#         self.password_hash = generate_password_hash(password)

#     def check_password(self, password):
#         return check_password_hash(self.password_hash, password)


# class News(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255))
#     date = db.Column(db.String(50))
#     category = db.Column(db.String(100))
#     image_filename = db.Column(db.String(255))
#     content = db.Column(db.Text)
#     image_caption = db.Column(db.String(255))
#     image_credit = db.Column(db.String(255))

#     @property
#     def image_url(self):
#         if self.image_filename:
#             return f"/static/uploads/{self.image_filename}"
#         else:
#             return "/static/uploads/default-placeholder.png"


# class Product(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255), nullable=False)
#     category = db.Column(db.String(100))
#     image_filename = db.Column(db.String(255))  # uploaded image
#     image_url = db.Column(db.String(255))       # external image URL
#     link_url = db.Column(db.String(255), nullable=False)  # product page URL

#     @property
#     def display_image(self):
#         if self.image_filename:
#             return f"/static/uploads/{self.image_filename}"
#         elif self.image_url:
#             return self.image_url
#         else:
#             return "/static/uploads/default-placeholder.png"


# @login_manager.user_loader
# def load_user(user_id):
#     return User.query.get(int(user_id))


# # Admin Views

# class MyAdminIndexView(AdminIndexView):
#     @expose('/')
#     @login_required
#     def index(self):
#         return super().index()

#     @expose('/logout')
#     def logout_view(self):
#         logout_user()
#         return redirect(url_for('login'))

#     def is_accessible(self):
#         return current_user.is_authenticated

#     def inaccessible_callback(self, name, **kwargs):
#         return redirect(url_for('login'))


# class NewsAdmin(ModelView):
#     upload_path = os.path.join(os.path.dirname(__file__), 'static/uploads')

#     form_extra_fields = {
#         'image_filename': FileUploadField(
#             'Upload News Image',
#             base_path=upload_path,
#             allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
#             namegen=lambda obj, file_data: secure_filename(file_data.filename)
#         )
#     }

#     column_list = ('id', 'title', 'date', 'category', 'image_filename', 'image_caption', 'image_credit', 'content')
#     column_searchable_list = ['title', 'category', 'content']
#     column_filters = ['category', 'date']
#     column_editable_list = ['title', 'category', 'date']
#     page_size = 20

#     def _list_thumbnail(self, context, model, name):
#         if not model.image_filename:
#             return ''
#         return Markup(f'<img src="/static/uploads/{model.image_filename}" style="max-height:100px;">')

#     column_formatters = {
#         'image_filename': _list_thumbnail
#     }

#     form_widget_args = {
#         'title': {'style': 'width: 50%;'},
#         'date': {'placeholder': 'e.g. July 14, 2025'},
#         'category': {'style': 'width: 30%;'},
#         'image_caption': {'style': 'width: 70%;'},
#         'image_credit': {'style': 'width: 70%;'},
#         'content': {'rows': 6, 'style': 'font-family: monospace; font-size: 0.9em;'},
#     }

#     form_args = {
#         'image_filename': {
#             'label': 'Upload News Image',
#             'help_text': 'Allowed formats: jpg, jpeg, png, gif. Max size 2MB.',
#         }
#     }

#     def is_accessible(self):
#         return current_user.is_authenticated

#     def inaccessible_callback(self, name, **kwargs):
#         return redirect(url_for('login'))


# class ProductAdmin(ModelView):
#     upload_path = os.path.join(os.path.dirname(__file__), 'static/uploads')

#     form_extra_fields = {
#         'image_filename': FileUploadField(
#             'Upload Image',
#             base_path=upload_path,
#             allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
#             namegen=lambda obj, file_data: secure_filename(file_data.filename)
#         )
#     }

#     column_list = ('id', 'title', 'category', 'image_filename', 'image_url', 'link_url')
#     column_searchable_list = ['title', 'category']
#     column_filters = ['category']
#     form_columns = ['title', 'category', 'image_filename', 'image_url', 'link_url']

#     form_widget_args = {
#         'title': {'style': 'width: 50%;'},
#         'category': {'style': 'width: 30%;'},
#         'image_url': {'placeholder': 'External image URL (optional)'},
#         'link_url': {'placeholder': 'Product page URL (required)'},
#     }

#     def _list_thumbnail(self, context, model, name):
#         if model.image_filename:
#             return Markup(f'<img src="/static/uploads/{model.image_filename}" style="max-height:100px;">')
#         elif model.image_url:
#             return Markup(f'<img src="{model.image_url}" style="max-height:100px;">')
#         return ''

#     column_formatters = {
#         'image_filename': _list_thumbnail,
#         'image_url': _list_thumbnail,
#     }

#     def is_accessible(self):
#         return current_user.is_authenticated

#     def inaccessible_callback(self, name, **kwargs):
#         return redirect(url_for('login'))


# admin = Admin(
#     app,
#     name='TCR Arena Admin',
#     template_mode='bootstrap4',
#     index_view=MyAdminIndexView(url='/admin')
# )

# admin.add_view(NewsAdmin(News, db.session))
# admin.add_view(ProductAdmin(Product, db.session))

# from flask_admin.menu import MenuLink
# admin.add_link(MenuLink(name='Visit Site', category='', url='/'))


# # Routes

# @app.route('/')
# def home():
#     news_items = News.query.order_by(News.id.desc()).limit(3).all()
#     products = Product.query.order_by(Product.id.desc()).limit(4).all()
#     welcome_text = "Welcome to TCR Arena - your hub for sports insights, collectibles, live scores, and exclusive content!"
#     return render_template('index.html', news_items=news_items, products=products, welcome_text=welcome_text)


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if current_user.is_authenticated:
#         return redirect(url_for('admin.index'))

#     if request.method == 'POST':
#         username = request.form.get('username')
#         password = request.form.get('password')
#         user = User.query.filter_by(username=username).first()
#         if user and user.check_password(password):
#             login_user(user)
#             flash('Logged in successfully.', 'success')
#             next_page = request.args.get('next')
#             return redirect(next_page or url_for('admin.index'))
#         else:
#             flash('Invalid username or password.', 'danger')
#     return render_template('login.html')


# @app.route('/logout')
# @login_required
# def logout():
#     logout_user()
#     flash('You have been logged out.', 'info')
#     return redirect(url_for('login'))


# # Terminal command to create admin user

# def create_admin():
#     with app.app_context():
#         username = input("Enter new admin username: ").strip()
#         if User.query.filter_by(username=username).first():
#             print(f"User '{username}' already exists.")
#             return
#         password = getpass.getpass("Enter password: ")
#         password_confirm = getpass.getpass("Confirm password: ")
#         if password != password_confirm:
#             print("Passwords do not match. Exiting.")
#             return
#         new_admin = User(username=username)
#         new_admin.set_password(password)
#         db.session.add(new_admin)
#         db.session.commit()
#         print(f"Admin user '{username}' created successfully.")


# if __name__ == '__main__':
#     upload_folder = os.path.join(os.path.dirname(__file__), 'static/uploads')
#     os.makedirs(upload_folder, exist_ok=True)

#     with app.app_context():
#         db.create_all()

#     if len(sys.argv) > 1 and sys.argv[1].lower() == "createadmin":
#         create_admin()
#     else:
#         app.run(debug=True)
import os
import sys
import getpass
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import FileUploadField
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import Markup
from flask_migrate import Migrate

app = Flask(__name__)

# Create instance folder if needed
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

db_path = os.path.join(app.instance_path, 'news.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'this-should-be-a-secret-key'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Models

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    date = db.Column(db.String(50))
    category = db.Column(db.String(100))
    image_filename = db.Column(db.String(255))
    content = db.Column(db.Text)
    image_caption = db.Column(db.String(255))
    image_credit = db.Column(db.String(255))

    @property
    def image_url(self):
        if self.image_filename:
            return f"/static/uploads/{self.image_filename}"
        else:
            return "/static/uploads/default-placeholder.png"


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    image_filename = db.Column(db.String(255))  # uploaded image
    image_url = db.Column(db.String(255))       # external image URL
    link_url = db.Column(db.String(255), nullable=False)  # product page URL

    @property
    def display_image(self):
        if self.image_filename:
            return f"/static/uploads/{self.image_filename}"
        elif self.image_url:
            return self.image_url
        else:
            return "/static/uploads/default-placeholder.png"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Admin Views

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    @login_required
    def index(self):
        return super().index()

    @expose('/logout')
    def logout_view(self):
        logout_user()
        return redirect(url_for('login'))

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))


class NewsAdmin(ModelView):
    upload_path = os.path.join(os.path.dirname(__file__), 'static/uploads')

    form_extra_fields = {
        'image_filename': FileUploadField(
            'Upload News Image',
            base_path=upload_path,
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
            namegen=lambda obj, file_data: secure_filename(file_data.filename)
        )
    }

    column_list = ('id', 'title', 'date', 'category', 'image_filename', 'image_caption', 'image_credit', 'content')
    column_searchable_list = ['title', 'category', 'content']
    column_filters = ['category', 'date']
    column_editable_list = ['title', 'category', 'date']
    page_size = 20

    def _list_thumbnail(self, context, model, name):
        if not model.image_filename:
            return ''
        return Markup(f'<img src="/static/uploads/{model.image_filename}" style="max-height:100px;">')

    column_formatters = {
        'image_filename': _list_thumbnail
    }

    form_widget_args = {
        'title': {'style': 'width: 50%;'},
        'date': {'placeholder': 'e.g. July 14, 2025'},
        'category': {'style': 'width: 30%;'},
        'image_caption': {'style': 'width: 70%;'},
        'image_credit': {'style': 'width: 70%;'},
        'content': {'rows': 6, 'style': 'font-family: monospace; font-size: 0.9em;'},
    }

    form_args = {
        'image_filename': {
            'label': 'Upload News Image',
            'help_text': 'Allowed formats: jpg, jpeg, png, gif. Max size 2MB.',
        }
    }

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))


class ProductAdmin(ModelView):
    upload_path = os.path.join(os.path.dirname(__file__), 'static/uploads')

    form_extra_fields = {
        'image_filename': FileUploadField(
            'Upload Image',
            base_path=upload_path,
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
            namegen=lambda obj, file_data: secure_filename(file_data.filename)
        )
    }

    column_list = ('id', 'title', 'category', 'image_filename', 'image_url', 'link_url')
    column_searchable_list = ['title', 'category']
    column_filters = ['category']
    form_columns = ['title', 'category', 'image_filename', 'image_url', 'link_url']

    form_widget_args = {
        'title': {'style': 'width: 50%;'},
        'category': {'style': 'width: 30%;'},
        'image_url': {'placeholder': 'External image URL (optional)'},
        'link_url': {'placeholder': 'Product page URL (required)'},
    }

    def _list_thumbnail(self, context, model, name):
        if model.image_filename:
            return Markup(f'<img src="/static/uploads/{model.image_filename}" style="max-height:100px;">')
        elif model.image_url:
            return Markup(f'<img src="{model.image_url}" style="max-height:100px;">')
        return ''

    column_formatters = {
        'image_filename': _list_thumbnail,
        'image_url': _list_thumbnail,
    }

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))


admin = Admin(
    app,
    name='TCR Arena Admin',
    template_mode='bootstrap4',
    index_view=MyAdminIndexView(url='/admin')
)

admin.add_view(NewsAdmin(News, db.session))
admin.add_view(ProductAdmin(Product, db.session))

from flask_admin.menu import MenuLink
admin.add_link(MenuLink(name='Visit Site', category='', url='/'))


# Routes

@app.route('/')
def home():
    news_items = News.query.order_by(News.id.desc()).limit(3).all()
    products = Product.query.order_by(Product.id.desc()).limit(4).all()
    welcome_text = "Welcome to TCR Arena - your hub for sports insights, collectibles, live scores, and exclusive content!"
    return render_template('index.html', news_items=news_items, products=products, welcome_text=welcome_text)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin.index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# New route to show full news article
@app.route('/news/<int:news_id>')
def view_news(news_id):
    news = News.query.get_or_404(news_id)
    # Show 3 other latest articles from the same category (excluding current)
    suggestions = News.query.filter(News.id != news_id, News.category == news.category).order_by(News.id.desc()).limit(3).all()
    return render_template('news_detail.html', news=news, suggestions=suggestions)



# New route for blog page with optional category filtering
# @app.route('/blog')
# def blog():
#     category = request.args.get('category')
#     page = request.args.get('page', 1, type=int)

#     if category:
#         query = News.query.filter_by(category=category)
#     else:
#         query = News.query

#     pagination = query.order_by(News.id.desc()).paginate(page=page, per_page=6)
#     news_items = pagination.items

#     categories = db.session.query(News.category).distinct().all()

#     return render_template('blog.html', news_items=news_items, categories=categories, pagination=pagination)
@app.route('/blog')
def blog():
    category = request.args.get('category')
    page = request.args.get('page', 1, type=int)

    if category:
        query = News.query.filter_by(category=category)
    else:
        query = News.query

    pagination = query.order_by(News.id.desc()).paginate(page=page, per_page=6)
    news_items = pagination.items

    categories = db.session.query(News.category).distinct().all()

    return render_template('blog.html', news_items=news_items, categories=categories, pagination=pagination)



# Terminal command to create admin user

def create_admin():
    with app.app_context():
        username = input("Enter new admin username: ").strip()
        if User.query.filter_by(username=username).first():
            print(f"User '{username}' already exists.")
            return
        password = getpass.getpass("Enter password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("Passwords do not match. Exiting.")
            return
        new_admin = User(username=username)
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()
        print(f"Admin user '{username}' created successfully.")


if __name__ == '__main__':
    upload_folder = os.path.join(os.path.dirname(__file__), 'static/uploads')
    os.makedirs(upload_folder, exist_ok=True)

    with app.app_context():
        db.create_all()

    if len(sys.argv) > 1 and sys.argv[1].lower() == "createadmin":
        create_admin()
    else:
        app.run(debug=True)
