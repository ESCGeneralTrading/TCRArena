import os
import sys
import getpass
from flask import Flask, jsonify, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import FileUploadField
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import Markup
from flask_migrate import Migrate
from flask import session
import re
from extensions import db
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Create instance folder if needed
try:
    os.makedirs(app.instance_path)
except OSError:
    pass


# db_path = os.path.join(app.instance_path, 'news.db')
# app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SECRET_KEY'] = 'this-should-be-a-secret-key'
# db = SQLAlchemy(app)
# migrate = Migrate(app, db)

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://tcrarena_db_user:ZLwPUckLOzUHE8Y07wQOTM2oPF7ooOkd@dpg-d25gn52li9vc73f9m400-a.singapore-postgres.render.com/tcrarena_db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'this-should-be-a-secret-key'
db.init_app(app)
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
    summary = db.Column(db.String(300))

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


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(200), nullable=False, server_default="")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)


class MemorabiliaStory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(300))
    image_url = db.Column(db.String(512)) 
    image_filename = db.Column(db.String(255))  # uploaded image filename
    image_credit = db.Column(db.String(100))
    date = db.Column(db.String(50))  # e.g., '2h', '5m'
    content = db.Column(db.Text)  

    def __repr__(self):
        return f"<MemorabiliaStory {self.title}>"

    @property
    def display_image(self):
        if self.image_filename:
            return f"/static/uploads/{self.image_filename}"
        elif self.image_url:
            return self.image_url
        else:
            return "/static/uploads/default-placeholder.png"

class YouTubeVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    video_id = db.Column(db.String(50), nullable=False)  # YouTube video ID only (not full URL)

    def __repr__(self):
        return f"<YouTubeVideo {self.title}>"


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

    column_list = ('id', 'title', 'date', 'category', 'image_filename', 'image_caption','summary', 'image_credit', 'content')
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
        'summary': {'rows': 3, 'style': 'width: 80%; font-size: 0.9em; font-family: monospace;'},
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

class MemorabiliaAdmin(ModelView):
    upload_path = os.path.join(os.path.dirname(__file__), 'static/uploads')

    form_extra_fields = {
        'image_filename': FileUploadField(
            'Upload Image',
            base_path=upload_path,
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
            namegen=lambda obj, file_data: secure_filename(file_data.filename)
        )
    }

    column_list = ('id', 'title', 'subtitle', 'image_credit', 'date', 'image_filename', 'image_url')
    column_searchable_list = ['title', 'image_credit']
    column_filters = ['image_credit', 'date']
    form_columns = ['title', 'subtitle', 'image_credit', 'date', 'image_filename', 'image_url', 'content']

    form_widget_args = {
    'content': {
        'rows': 6,
        'style': 'font-family: monospace; font-size: 0.9em;'
        }
    }


    def _list_thumbnail(self, context, model, name):
        if model.image_filename:
            return Markup(f'<img src="/static/uploads/{model.image_filename}" style="max-height:100px;">')
        elif model.image_url:
            return Markup(f'<img src="{model.image_url}" style="max-height:100px;">')
        return ''

    column_formatters = {
        'image_filename': _list_thumbnail,
        'image_url': _list_thumbnail
    }

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(MemorabiliaAdmin(MemorabiliaStory, db.session))


class ContactAdmin(ModelView):
    column_list = ('id', 'name', 'email', 'contact_number','message')
    form_columns = ['name', 'email', 'contact_number','message']
    column_searchable_list = ['name', 'email', 'contact_number']
    column_filters = ['email']
    page_size = 20

    can_edit = False
    can_create = False

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(ContactAdmin(Contact, db.session))

from flask_admin.menu import MenuLink
admin.add_link(MenuLink(name='Visit Site', category='', url='/'))
admin.add_link(MenuLink(name='Logout', category='', url='logout/'))

class SubscriberAdmin(ModelView):
    column_list = ('id', 'email')
    form_columns = ['email']
    can_edit = False
    can_create = False
    can_delete = True

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(SubscriberAdmin(Subscriber, db.session))

class YouTubeVideoAdmin(ModelView):
    column_list = ('id', 'title', 'video_id')
    form_columns = ['title', 'video_id']
    column_searchable_list = ['title']
    page_size = 20

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(YouTubeVideoAdmin(YouTubeVideo, db.session))


# Routes

@app.route('/live-scores')
def live_scores():
    api_key = 'c5ca24a68253418f9c95e742090894bf'

    if not api_key:
        return jsonify({"error": "API key not configured"}), 500

    url = "https://api.football-data.org/v4/matches?status=LIVE"
    headers = {
        'X-Auth-Token': api_key
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        live_matches = []
        matches = data.get('matches', [])

        if not matches:
            return jsonify([])  # No live matches now

        for match in matches:
            live_matches.append({
                "competition": match['competition']['name'],
                "home_team": match['homeTeam']['name'],
                "away_team": match['awayTeam']['name'],
                "score": f"{match['score']['fullTime']['home']} - {match['score']['fullTime']['away']}",
                "status": match['status'],
                "minute": match.get('minute', 'N/A')
            })

        return jsonify(live_matches)

    except requests.RequestException as e:
        return jsonify({"error": "Failed to fetch live scores", "details": str(e)}), 500

@app.route('/')
def home():
    news_items = News.query.order_by(News.id.desc()).limit(6).all()
    products = Product.query.order_by(Product.id.desc()).limit(5).all()
    memorabilia_stories = MemorabiliaStory.query.order_by(MemorabiliaStory.id.desc()).limit(6).all()
    youtube_videos = YouTubeVideo.query.order_by(YouTubeVideo.id.desc()).limit(5).all()
    welcome_text = "Welcome to TCR Arena - your hub for sports insights, collectibles, live scores, and exclusive content!"
    return render_template('index.html', news_items=news_items, products=products, memorabilia_stories=memorabilia_stories,youtube_videos=youtube_videos,welcome_text=welcome_text)

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

import requests
from flask import jsonify

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# New route to show full news article
# @app.route('/news/<int:news_id>')
# def view_news(news_id):
#     if not session.get('joined'):
#         return redirect(url_for('join', next=request.path))

#     news = News.query.get_or_404(news_id)
#     suggestions = News.query.filter(News.id != news_id, News.category == news.category).order_by(News.id.desc()).limit(3).all()
#     return render_template('news_detail.html', news=news, suggestions=suggestions)
@app.route('/news/<int:news_id>')
def view_news(news_id):
    # Remove this condition ↓↓↓
    # if not session.get('joined'):
    #     return redirect(url_for('join', next=request.path))

    news = News.query.get_or_404(news_id)
    suggestions = News.query.filter(News.id != news_id, News.category == news.category).order_by(News.id.desc()).limit(3).all()
    return render_template('news_detail.html', news=news, suggestions=suggestions)


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



def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def validate_phone(phone):
    return re.match(r"^\+?\d{7,15}$", phone)

@app.route('/memorabilia')
def memorabilia():
    page = request.args.get('page', 1, type=int)
    pagination = MemorabiliaStory.query.order_by(MemorabiliaStory.date.desc()).paginate(page=page, per_page=9)
    return render_template(
        'memorabilia.html',
        memorabilia_stories=pagination.items,
        pagination=pagination
    )

@app.route('/join', methods=['GET', 'POST'])
def join():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        contact_number = request.form.get('contact_number', '').strip()
        message = request.form.get('message', '').strip()

        # Validation
        if not name or not email or not contact_number:
            flash("All fields are required.", "danger")
        elif not validate_email(email):
            flash("Invalid email address.", "danger")
        elif not validate_phone(contact_number):
            flash("Invalid phone number format.", "danger")
        else:
            new_contact = Contact(name=name, email=email, contact_number=contact_number, message=message)
            db.session.add(new_contact)
            db.session.commit()
            session['joined'] = True
            flash("Thanks for the submission!", "success")
            return redirect(request.args.get("next") or url_for('home'))

    return render_template('join.html')

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email', '').strip()

    if not email:
        flash("Email is required.", "danger")
    elif not validate_email(email):
        flash("Invalid email address.", "danger")
    else:
        # Prevent duplicate subscriptions
        if Subscriber.query.filter_by(email=email).first():
            flash("You are already subscribed!", "info")
        else:
            new_subscriber = Subscriber(email=email)
            db.session.add(new_subscriber)
            db.session.commit()
            flash("Thank you for subscribing!", "success")

    return redirect(url_for('home'))

@app.route('/add-memorabilia', methods=['GET', 'POST'])
def add_memorabilia():
    if request.method == 'POST':
        title = request.form['title']
        subtitle = request.form.get('subtitle')
        image_credit = request.form.get('image_credit')
        date = request.form.get('date')
        image_url = request.form.get('image_url')
        image = request.files.get('image')

        filename = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        story = MemorabiliaStory(
            title=title,
            subtitle=subtitle,
            image_credit=image_credit,
            date=date,
            image_url=image_url if not filename else None,
            image_filename=filename
        )
        db.session.add(story)
        db.session.commit()
        flash("Memorabilia story added!", "success")
        return redirect(url_for('home'))

    return render_template('add_memorabilia.html')
    
@app.route('/memorabilia/<int:item_id>')
def view_memorabilia(item_id):
    item = MemorabiliaStory.query.get_or_404(item_id)
    suggestions = MemorabiliaStory.query.filter(MemorabiliaStory.id != item_id).order_by(MemorabiliaStory.id.desc()).limit(3).all()
    return render_template('memorabilia_detail.html', item=item, suggestions=suggestions)


@app.route('/videos')
def all_videos():
    videos = YouTubeVideo.query.order_by(YouTubeVideo.id.desc()).all()
    return render_template('all_videos.html', videos=videos)

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


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
        # app.run(debug=True)
        app.run(host='0.0.0.0', port=5002, debug=True, use_debugger=False, use_reloader=True)





