import datetime  # instead of "from datetime import datetime, timedelta"
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
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

load_dotenv()

app = Flask(__name__)

# Create instance folder if needed
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

today = datetime.datetime.now().date()


app.config['MAIL_SERVER'] = 'smtp.titan.email'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'digital@thecollectroom.com'
app.config['MAIL_PASSWORD'] = 'ESC@2025'
app.config['MAIL_DEFAULT_SENDER'] = ('TCR Collectors', 'digital@thecollectroom.com')

mail = Mail(app)


ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg'}
API_KEY = "538e881e9f4c4cb1d74708ddd91c6aa4"

LIVE_FEED_URL = f"http://www.goalserve.com/getfeed/{API_KEY}/soccernew/live?json=1"
LEAGUES_URL = f"https://www.goalserve.com/getfeed/{API_KEY}/soccerfixtures/data/mapping?json=1"
LEAGUE_TEAMS_URL = f"https://www.goalserve.com/getfeed/{API_KEY}/soccerleague/{{}}?json=1"  # leagueID
PLAYER_URL = f"https://www.goalserve.com/getfeed/{API_KEY}/player/{{}}?json=1"

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Limit max upload size (e.g., 50MB)

db_path = os.path.join(app.instance_path, 'news.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'this-should-be-a-secret-key'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://tcrarena_db_user:ZLwPUckLOzUHE8Y07wQOTM2oPF7ooOkd@dpg-d25gn52li9vc73f9m400-a.singapore-postgres.render.com/tcrarena_db"
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SECRET_KEY'] = 'this-should-be-a-secret-key'
# db.init_app(app)
# migrate = Migrate(app, db)

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
    image_filename = db.Column(db.String(255))
    video_filename = db.Column(db.String(255))
    video_url = db.Column(db.String(512))
    image_credit = db.Column(db.String(100))
    date = db.Column(db.String(50))
    content = db.Column(db.Text)
    
    likes = db.Column(db.Integer, default=200) 
    
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

    @property
    def display_video(self):
        if self.video_filename:
            return f"/static/uploads/{self.video_filename}"
        elif self.video_url:
            return self.video_url
        else:
            return None
        
class CollectorJoinee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    join_date = db.Column(db.DateTime, default=db.func.now())

class CollectorVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(300))
    video_filename = db.Column(db.String(255))  # uploaded video
    video_url = db.Column(db.String(512))       # optional external video URL
    date = db.Column(db.String(50))
    content = db.Column(db.Text)
    likes = db.Column(db.Integer, default=300)
   
    def __repr__(self):
        return f"<CollectorVideo {self.title}>"

    @property
    def display_video(self):
        if self.video_filename:
            return f"/static/uploads/{self.video_filename}"
        elif self.video_url:
            return self.video_url
        return None

class YouTubeVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    video_id = db.Column(db.String(50), nullable=False)  # YouTube ID only
    is_short = db.Column(db.Boolean, default=True)       # True = Shorts, False = Full-length

    def __repr__(self):
        return f"<YouTubeVideo {self.title}>"

# --- Advertisement model ---
class Advertisement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))                # optional title
    details = db.Column(db.Text)                     # optional details/content
    image_filename = db.Column(db.String(255))       # uploaded image filename
    image_url = db.Column(db.String(512))            # external image URL (optional)
    video_filename = db.Column(db.String(255))       # uploaded video filename
    video_url = db.Column(db.String(512))            # external video URL (optional)
    start_date = db.Column(db.String(50))            # optional scheduling (string for simplicity)
    end_date = db.Column(db.String(50))              # optional scheduling (string for simplicity)
    active = db.Column(db.Boolean, default=True)     # simple active toggle

    def display_image(self):
        if self.image_filename:
            return f"/static/uploads/{self.image_filename}"
        elif self.image_url:
            return self.image_url
        return None

    def display_video(self):
        if self.video_filename:
            return f"/static/uploads/{self.video_filename}"
        elif self.video_url:
            return self.video_url
        return None


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
        ),
        'video_filename': FileUploadField(
            'Upload Video',
            base_path=upload_path,
            allowed_extensions=['mp4','mp3', 'webm', 'ogg'],  # Allowed video formats
            namegen=lambda obj, file_data: secure_filename(file_data.filename)
        )
    }


    column_list = ('id', 'title', 'subtitle', 'image_credit', 'date', 'likes', 'image_filename', 'image_url', 'video_filename', 'video_url')
    column_searchable_list = ['title', 'image_credit']
    column_filters = ['image_credit', 'date']
    form_columns = ['title', 'subtitle', 'image_credit', 'date', 'likes', 'image_filename', 'image_url', 'video_filename', 'video_url', 'content']

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
        elif model.video_filename:
            return Markup(f'''
                <video width="150" controls>
                    <source src="/static/uploads/{model.video_filename}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            ''')
        elif model.video_url:
            return Markup(f'<a href="{model.video_url}" target="_blank">Video Link</a>')
        return ''

    column_formatters = {
        'image_filename': _list_thumbnail,
        'image_url': _list_thumbnail,
        'video_filename': _list_thumbnail,
        'video_url': _list_thumbnail,
    }

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))
admin.add_view(MemorabiliaAdmin(MemorabiliaStory, db.session))

class CollectorVideoAdmin(ModelView):
    upload_path = os.path.join(os.path.dirname(__file__), 'static/uploads')

    form_extra_fields = {
        'video_filename': FileUploadField(
            'Upload Video',
            base_path=upload_path,
            allowed_extensions=['mp4','webm','ogg'],
            namegen=lambda obj, file_data: secure_filename(file_data.filename)
        )
    }

    column_list = ('id', 'title', 'subtitle', 'date', 'likes', 'video_filename', 'video_url')
    form_columns = ['title', 'subtitle', 'date', 'likes', 'video_filename', 'video_url', 'content']

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(CollectorVideoAdmin(CollectorVideo, db.session))

class CollectorJoineeAdmin(ModelView):
    column_list = ('id', 'name', 'email', 'join_date')
    column_searchable_list = ['name', 'email']
    column_filters = ['join_date']
    form_columns = ['name', 'email']

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(CollectorJoineeAdmin(CollectorJoinee, db.session))

# --- Advertisement admin view ---
class AdvertisementAdmin(ModelView):
    upload_path = os.path.join(os.path.dirname(__file__), 'static/uploads')

    form_extra_fields = {
        'image_filename': FileUploadField(
            'Upload Image',
            base_path=upload_path,
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
            namegen=lambda obj, file_data: secure_filename(file_data.filename)
        ),
        'video_filename': FileUploadField(
            'Upload Video',
            base_path=upload_path,
            allowed_extensions=['mp4','mp3' 'webm', 'ogg'],
            namegen=lambda obj, file_data: secure_filename(file_data.filename)
        )
    }

    column_list = ('id', 'title', 'active', 'start_date', 'end_date', 'image_filename', 'image_url', 'video_filename', 'video_url')
    form_columns = ['title', 'details', 'active', 'start_date', 'end_date', 'image_filename', 'image_url', 'video_filename', 'video_url']

    form_widget_args = {
        'title': {'style': 'width: 70%;'},
        'details': {'rows': 4, 'style': 'width: 90%;'},
        'image_url': {'placeholder': 'External image URL (optional)'},
        'video_url': {'placeholder': 'External video URL (optional)'},
    }

    def _list_thumbnail(self, context, model, name):
        if model.image_filename:
            return Markup(f'<img src="/static/uploads/{model.image_filename}" style="max-height:120px;">')
        elif model.image_url:
            return Markup(f'<img src="{model.image_url}" style="max-height:120px;">')
        elif model.video_filename:
            return Markup(f'<video width="160" controls><source src="/static/uploads/{model.video_filename}" type="video/mp4">Your browser does not support video.</video>')
        elif model.video_url:
            return Markup(f'<a href="{model.video_url}" target="_blank">Video Link</a>')
        return ''

    column_formatters = {
        'image_filename': _list_thumbnail,
        'image_url': _list_thumbnail,
        'video_filename': _list_thumbnail,
        'video_url': _list_thumbnail,
    }

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

# register in admin:
admin.add_view(AdvertisementAdmin(Advertisement, db.session))

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

# class YouTubeVideoAdmin(ModelView):
#     column_list = ('id', 'title', 'video_id')
#     form_columns = ['title', 'video_id']
#     column_searchable_list = ['title']
#     page_size = 20

#     def is_accessible(self):
#         return current_user.is_authenticated

#     def inaccessible_callback(self, name, **kwargs):
#         return redirect(url_for('login'))

# admin.add_view(YouTubeVideoAdmin(YouTubeVideo, db.session))
class YouTubeVideoAdmin(ModelView):
    column_list = ('id', 'title', 'video_id', 'is_short')  # <-- added is_short
    form_columns = ['title', 'video_id', 'is_short']      # <-- added is_short
    column_searchable_list = ['title']
    page_size = 20

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(YouTubeVideoAdmin(YouTubeVideo, db.session))
# ====================
# --- LIVE SCORES ---
# ====================
LIVE_FEED_URL = "http://www.goalserve.com/getfeed/538e881e9f4c4cb1d74708ddd91c6aa4/soccernew/live?json=1"

def date_to_day_code(input_date_str):
    try:
        input_date = datetime.datetime.strptime(input_date_str, "%d/%m/%Y").date()
    except ValueError:
        return None
    today = datetime.datetime.now().date()
    delta = (input_date - today).days
    return f"d{delta}"

def get_dynamic_feed_url(day_code):
    base_url = "http://www.goalserve.com/getfeed/538e881e9f4c4cb1d74708ddd91c6aa4/soccernew/"
    if day_code == "d0":
        return f"{base_url}home?json=1"  # use live feed for today
    return f"{base_url}{day_code}?json=1"

def sort_matches(matches):
    def match_key(m):
        if m['status'] in ['FT', 'Finished']:
            return (0, datetime.datetime.min.time())
        try:
            t = datetime.datetime.strptime(m['time'], "%H:%M").time()
        except:
            t = datetime.datetime.max.time()
        return (1, t)
    return sorted(matches, key=match_key)

def fetch_matches(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return None, str(e)
    matches_list = []
    categories = data.get('scores', {}).get('category', [])
    if isinstance(categories, dict):
        categories = [categories]

    for cat in categories:
        league_name = cat.get('@name', 'Unknown League')
        league_id = cat.get('@id', '')  # capture league ID
        matches = cat.get('matches', {}).get('match', [])
        if isinstance(matches, dict):
            matches = [matches]
        for match in matches:
            raw_date = match.get('@date', '')
            try:
                date_obj = datetime.strptime(raw_date, "%b %d")
                formatted_date = date_obj.strftime("%d/%m")
            except:
                formatted_date = raw_date
            events_raw = match.get('events') or {}
            events_data = events_raw.get('event', [])
            if isinstance(events_data, dict):
                events_data = [events_data]
            events = []
            for ev in events_data:
                events.append({
                    'minute': ev.get('@minute', ''),
                    'extra_min': ev.get('@extra_min', ''),
                    'type': ev.get('@type', ''),
                    'team': ev.get('@team', ''),
                    'player': ev.get('@player', ''),
                    'assist': ev.get('@assist', ''),
                    'result': ev.get('@result', '')
                })
            matches_list.append({
                'league': league_name,
                'league_id': league_id,  # store it
                'venue': match.get('@venue', ''),
                'local_team': match.get('localteam', {}).get('@name', ''),
                'local_goals': match.get('localteam', {}).get('@goals', 0),
                'visitor_team': match.get('visitorteam', {}).get('@name', ''),
                'visitor_goals': match.get('visitorteam', {}).get('@goals', 0),
                'status': match.get('@status', 'NS'),
                'time': match.get('@time', ''),
                'date': formatted_date,
                'events': events,
                'match_id': match.get('@id', '')
            })
    return matches_list, None
# def fetch_matches(url):
#     try:
#         response = requests.get(url, timeout=10)
#         response.raise_for_status()
#         data = response.json()
#     except requests.exceptions.RequestException as e:
#         return None, str(e)

#     matches_list = []
#     categories = data.get('scores', {}).get('category', [])
#     if isinstance(categories, dict):
#         categories = [categories]

#     for cat in categories:
#         league_name = cat.get('@name', 'Unknown League')
#         matches = cat.get('matches', {}).get('match', [])
#         if isinstance(matches, dict):
#             matches = [matches]

#         for match in matches:
#             raw_date = match.get('@date', '')
#             try:
#                 date_obj = datetime.datetime.strptime(raw_date, "%b %d")
#                 formatted_date = date_obj.strftime("%d/%m")
#             except:
#                 formatted_date = raw_date

#             events_raw = match.get('events') or {}
#             events_data = events_raw.get('event', [])
#             if isinstance(events_data, dict):
#                 events_data = [events_data]

#             events = []
#             for ev in events_data:
#                 events.append({
#                     'minute': ev.get('@minute', ''),
#                     'extra_min': ev.get('@extra_min', ''),
#                     'type': ev.get('@type', ''),
#                     'team': ev.get('@team', ''),
#                     'player': ev.get('@player', ''),
#                     'assist': ev.get('@assist', ''),
#                     'result': ev.get('@result', '')
#                 })

#             matches_list.append({
#                 'league': league_name,
#                 'venue': match.get('@venue', ''),
#                 'local_team': match.get('localteam', {}).get('@name', ''),
#                 'local_goals': match.get('localteam', {}).get('@goals', 0),
#                 'visitor_team': match.get('visitorteam', {}).get('@name', ''),
#                 'visitor_goals': match.get('visitorteam', {}).get('@goals', 0),
#                 'status': match.get('@status', 'NS'),
#                 'time': match.get('@time', ''),
#                 'date': formatted_date,
#                 'events': events
#             })
#     return matches_list, None

def fetch_json(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as e:
        return None, str(e)
# Routes

@app.route('/live-scores')
def live_scores():
    matches, error = fetch_matches(LIVE_FEED_URL)
    if matches:
        matches = sort_matches(matches)
    if error:
        return jsonify({"error": error}), 500
    return jsonify(matches)

@app.route('/all-scores')
def all_scores():
    matches, error = fetch_matches(LIVE_FEED_URL)
    if matches:
        matches = sort_matches(matches)
    return render_template('all_scores.html', live_matches=matches or [], live_error=error)

@app.route('/search')
def search_matches():
    input_date = request.args.get('date', '').strip()  # format: dd/mm/yyyy
    day_code = date_to_day_code(input_date)
    if not day_code:
        return jsonify({"error": "Invalid date format. Use dd/mm/yyyy"}), 400

    try:
        date_obj = datetime.datetime.strptime(input_date, "%d/%m/%Y").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use dd/mm/yyyy"}), 400

    today = datetime.datetime.now().date()
    if not (today - datetime.timedelta(days=7) <= date_obj <= today + datetime.timedelta(days=7)):
        return jsonify({"error": "Only dates within past 7 or next 7 days are allowed."}), 400

    url = get_dynamic_feed_url(day_code)
    matches, error = fetch_matches(url)
    if matches:
        matches = sort_matches(matches)

    if error:
        return jsonify({"error": error}), 500

    return jsonify({"matches": matches})
@app.route('/leagues')
def leagues():
    data, error = fetch_json(LEAGUES_URL)
    if error:
        return f"Error fetching leagues: {error}", 500
    leagues_list = data.get('fixtures', {}).get('mapping', [])
    if isinstance(leagues_list, dict):
        leagues_list = [leagues_list]
    return render_template('leagues.html', leagues=leagues_list)

@app.route('/league/<league_id>')
def league_details(league_id):
    url = LEAGUE_TEAMS_URL.format(league_id)
    data, error = fetch_json(url)
    if error:
        return f"Error fetching league details: {error}", 500

    league = data.get('league', {})
    teams = league.get('team', [])
    if isinstance(teams, dict):
        teams = [teams]

    # Flatten player info per team
    for team in teams:
        squad = team.get('squad', {}).get('player', [])
        if isinstance(squad, dict):
            squad = [squad]
        team['squad'] = squad
        team['coach'] = team.get('coach', {"@name": "N/A", "@id": ""})

    return render_template('league_teams.html', league=league, teams=teams)

@app.route('/team/<league_id>/<team_name>')
def team_details(league_id, team_name):
    url = LEAGUE_TEAMS_URL.format(league_id)
    data, error = fetch_json(url)
    if error:
        return f"Error fetching team details: {error}", 500

    league = data.get('league', {}) 
    teams = league.get('team', [])
    if isinstance(teams, dict):
        teams = [teams]

    selected_team = None
    for team in teams:
        if team.get('@name', '').lower() == team_name.lower():
            squad = team.get('squad', {}).get('player', [])
            if isinstance(squad, dict):
                squad = [squad]
            team['squad'] = squad
            team['coach'] = team.get('coach', {"@name": "N/A", "@id": ""})
            selected_team = team
            break

    if not selected_team:
        return render_template(
            'error.html',
            error_code=404,
            message=f"Team '{team_name}' not found in league {league.get('@name', '')}"
        ), 404


    return render_template('team_details.html', league=league, team=selected_team)


# @app.route('/')
# def home():
#     news_items = News.query.order_by(News.id.desc()).limit(6).all()
#     products = Product.query.order_by(Product.id.desc()).limit(5).all()
#     memorabilia_stories = MemorabiliaStory.query.order_by(MemorabiliaStory.id.desc()).limit(6).all()
#     youtube_videos = YouTubeVideo.query.order_by(YouTubeVideo.id.desc()).limit(5).all()
#     ad = Advertisement.query.filter_by(active=True).order_by(Advertisement.id.desc()).first()
#     welcome_text = "Welcome to TCR Arena - your hub for sports insights, collectibles, live scores, and exclusive content!"
#     return render_template('index.html', news_items=news_items, products=products, memorabilia_stories=memorabilia_stories,youtube_videos=youtube_videos,advertisement=ad,welcome_text=welcome_text)

# --- TCR Home Page ---
# @app.route('/')
# def home():
#     news_items = News.query.order_by(News.id.desc()).limit(6).all()
#     products = Product.query.order_by(Product.id.desc()).limit(5).all()
#     memorabilia_stories = MemorabiliaStory.query.order_by(MemorabiliaStory.id.desc()).limit(6).all()
#     youtube_videos = YouTubeVideo.query.order_by(YouTubeVideo.id.desc()).limit(5).all()
#     ad = Advertisement.query.filter_by(active=True).order_by(Advertisement.id.desc()).first()
#     live_matches, live_error = fetch_matches(LIVE_FEED_URL)
#     if live_matches:
#         live_matches = sort_matches(live_matches)
#     welcome_text = "Welcome to TCR Arena - your hub for sports insights, collectibles, live scores, and exclusive content!"
#     return render_template(
#         'index.html',
#         news_items=news_items,
#         products=products,
#         memorabilia_stories=memorabilia_stories,
#         youtube_videos=youtube_videos,
#         advertisement=ad,
#         welcome_text=welcome_text,
#         live_matches=live_matches or [],
#         live_error=live_error
#     )
@app.route('/')
def home():
    news_items = News.query.order_by(News.id.desc()).limit(6).all()
    products = Product.query.order_by(Product.id.desc()).limit(5).all()
    memorabilia_stories = MemorabiliaStory.query.order_by(MemorabiliaStory.id.desc()).limit(6).all()
    youtube_shorts = YouTubeVideo.query.filter_by(is_short=True).order_by(YouTubeVideo.id.desc()).limit(5).all()
    ad = Advertisement.query.filter_by(active=True).order_by(Advertisement.id.desc()).first()
    live_matches, live_error = fetch_matches(LIVE_FEED_URL)
    if live_matches:
        live_matches = sort_matches(live_matches)
    welcome_text = "Welcome to TCR Arena - your hub for sports insights, collectibles, live scores, and exclusive content!"
    return render_template(
        'index.html',
        news_items=news_items,
        products=products,
        memorabilia_stories=memorabilia_stories,
        youtube_videos=youtube_shorts,
        advertisement=ad,
        welcome_text=welcome_text,
        live_matches=live_matches or [],
        live_error=live_error
    )

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
@app.route('/news/<int:news_id>')
def view_news(news_id):
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

# @app.route('/memorabilia')
# def memorabilia():
#     page = request.args.get('page', 1, type=int)
#     pagination = MemorabiliaStory.query.order_by(MemorabiliaStory.date.desc()).paginate(page=page, per_page=10)
#     return render_template(
#         'memorabilia.html',
#         memorabilia_stories=pagination.items,
#         pagination=pagination
#     )

# @app.route('/memorabilia')
# def memorabilia():
#     page = request.args.get('page', 1, type=int)
#     pagination = MemorabiliaStory.query.order_by(MemorabiliaStory.date.desc()).paginate(page=page, per_page=11)
#     collector_videos = CollectorVideo.query.order_by(CollectorVideo.date.desc()).limit(10).all()
#     return render_template(
#         'memorabilia.html',
#         memorabilia_stories=pagination.items,
#         pagination=pagination,
#         collector_videos=collector_videos
#     )
@app.route('/memorabilia')
def memorabilia():
    page = request.args.get('page', 1, type=int)
    videos_per_page = 4
    images_per_page = 6

    # Fetch all items ordered by date
    all_items = MemorabiliaStory.query.order_by(MemorabiliaStory.date.desc()).all()
    all_videos = [item for item in all_items if item.display_video]
    all_images = [item for item in all_items if not item.display_video]

    # Sort images by id
    all_images.sort(key=lambda x: x.id, reverse=True)


    # Paginate videos and images separately
    video_start = (page - 1) * videos_per_page
    video_end = video_start + videos_per_page
    image_start = (page - 1) * images_per_page
    image_end = image_start + images_per_page

    videos = all_videos[video_start:video_end]
    images = all_images[image_start:image_end]

    # Calculate total pages based on the list that requires more pages
    total_video_pages = (len(all_videos) + videos_per_page - 1) // videos_per_page
    total_image_pages = (len(all_images) + images_per_page - 1) // images_per_page
    total_pages = max(total_video_pages, total_image_pages)

    # Pagination object
    class Pagination:
        def __init__(self, page, total_pages):
            self.page = page
            self.pages = total_pages

        @property
        def has_prev(self):
            return self.page > 1

        @property
        def has_next(self):
            return self.page < self.pages

        @property
        def prev_num(self):
            return self.page - 1

        @property
        def next_num(self):
            return self.page + 1

        def iter_pages(self):
            return range(1, self.pages + 1)

    pagination = Pagination(page=page, total_pages=total_pages)
    collector_videos = CollectorVideo.query.order_by(CollectorVideo.date.desc()).limit(10).all()

    return render_template(
        'memorabilia.html',
        videos=videos,
        images=images,
        pagination=pagination,
        memorabilia_stories=videos + images,
        collector_videos=collector_videos
    )

# @app.route('/memorabilia')
# def memorabilia():
#     page = request.args.get('page', 1, type=int)
#     videos_per_page = 4
#     images_per_page = 6

#     # Fetch all items ordered by date
#     all_items = MemorabiliaStory.query.order_by(MemorabiliaStory.date.desc()).all()
#     all_videos = [item for item in all_items if item.display_video]
#     all_images = [item for item in all_items if not item.display_video]

#     # Paginate videos and images separately
#     video_start = (page - 1) * videos_per_page
#     video_end = video_start + videos_per_page
#     image_start = (page - 1) * images_per_page
#     image_end = image_start + images_per_page

#     videos = all_videos[video_start:video_end]
#     images = all_images[image_start:image_end]

#     # Calculate total pages based on the list that requires more pages
#     total_video_pages = (len(all_videos) + videos_per_page - 1) // videos_per_page
#     total_image_pages = (len(all_images) + images_per_page - 1) // images_per_page
#     total_pages = max(total_video_pages, total_image_pages)

#     # Pagination object
#     class Pagination:
#         def __init__(self, page, total_pages):
#             self.page = page
#             self.pages = total_pages

#         @property
#         def has_prev(self):
#             return self.page > 1

#         @property
#         def has_next(self):
#             return self.page < self.pages

#         @property
#         def prev_num(self):
#             return self.page - 1

#         @property
#         def next_num(self):
#             return self.page + 1

#         def iter_pages(self):
#             return range(1, self.pages + 1)

#     pagination = Pagination(page=page, total_pages=total_pages)
#     collector_videos = CollectorVideo.query.order_by(CollectorVideo.date.desc()).limit(10).all()

#     return render_template(
#         'memorabilia.html',
#         videos=videos,
#         images=images,
#         pagination=pagination,
#         memorabilia_stories=videos + images,
#         collector_videos=collector_videos
#     )



from flask import session

# --- Format Likes Helper ---
def format_likes(num):
    if num is None:
        return "0"
    if num < 1000:
        return str(num)
    elif num < 1_000_000:
        return f"{num/1000:.1f}k".rstrip("0").rstrip(".")
    else:
        return f"{num/1_000_000:.1f}M".rstrip("0").rstrip(".")

# Register as Jinja filter
app.jinja_env.filters['format_likes'] = format_likes


@app.route('/like/memorabilia/<int:item_id>', methods=['POST'])
def like_memorabilia(item_id):
    item = MemorabiliaStory.query.get(item_id)
    if not item:
        return {"error": "Item not found"}, 404

    # Track liked items in session
    liked_items = session.get('liked_memorabilia', [])

    if item_id in liked_items:
        return {"error": "Already liked"}, 400

    if item.likes is None:
        item.likes = 0

    item.likes += 1
    db.session.commit()

    # Mark this item as liked in session
    liked_items.append(item_id)
    session['liked_memorabilia'] = liked_items

    return {"likes": item.likes}


@app.route("/like/collector/<int:video_id>", methods=["POST"])
def like_collector(video_id):
    video = CollectorVideo.query.get(video_id)
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    liked_videos = session.get('liked_collector', [])

    if video_id in liked_videos:
        return jsonify({"error": "Already liked"}), 400

    if video.likes is None:
        video.likes = 0

    video.likes += 1
    db.session.commit()

    liked_videos.append(video_id)
    session['liked_collector'] = liked_videos

    return jsonify({"likes": video.likes})



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
        video_url = request.form.get('video_url')

        image = request.files.get('image')
        video = request.files.get('video')

        filename_img = None
        filename_vid = None

        if image and allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename_img = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_img))

        if video and allowed_file(video.filename, ALLOWED_VIDEO_EXTENSIONS):
            filename_vid = secure_filename(video.filename)
            video.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_vid))

        story = MemorabiliaStory(
            title=title,
            subtitle=subtitle,
            image_credit=image_credit,
            date=date,
            image_url=image_url if not filename_img else None,
            video_url=video_url if not filename_vid else None,
            image_filename=filename_img,
            video_filename=filename_vid,
            content=request.form.get('content')
        )
        db.session.add(story)
        db.session.commit()
        flash("Memorabilia story added!", "success")
        return redirect(url_for('home'))

    return render_template('memorabilia.html')
    
@app.route('/memorabilia/<int:item_id>')
def view_memorabilia(item_id):
    item = MemorabiliaStory.query.get_or_404(item_id)
    suggestions = MemorabiliaStory.query.filter(MemorabiliaStory.id != item_id).order_by(MemorabiliaStory.id.desc()).limit(3).all()
    return render_template('memorabilia_detail.html', item=item, suggestions=suggestions)

@app.route('/join-collectors', methods=['POST'])
def join_collectors():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()

    if not email:
        flash("Email is required!", "danger")
        return redirect(request.referrer or url_for('home'))

    existing = CollectorJoinee.query.filter_by(email=email).first()
    if existing:
        flash("You have already joined the TCR Collectors Community!", "info")
        return redirect(request.referrer or url_for('home'))

    # Add new collector joinee
    new_joinee = CollectorJoinee(name=name if name else None, email=email)
    db.session.add(new_joinee)
    db.session.commit()

    # Prepare email content
    collector_name = name if name else "Collector"
    msg = Message(
        "Your Exclusive 20% Collector's Discount 🎉",
        recipients=[email]
    )
    msg.body = (
        f"Dear {collector_name},\n\n"
        "Welcome to the TCR Collectors Community!\n"
        "As a valued member, you now have access to exclusive stories, rare finds, "
        "and special collector events.\n\n"
        "Here’s your personal 20% discount code: TCRCOLLECTOR20\n"
        "Use it at checkout on our website https://www.thecollectroom.com/ or our shop \"The Collect Room\" to expand your collection at a special rate.\n\n"
        "We can’t wait to see what you collect next!\n\n"
        "Happy collecting,\n"
        "The TCR Team"
    )


    msg.html = f"""
    <p>Dear {collector_name},</p>
    <p>Welcome to the <strong>TCR Collectors Community</strong>!</p>
    <p>As a valued member, you now have access to exclusive stories, rare finds, and special collector events.</p>
    <p style="font-size:1.2rem; color:#021638;">
        <strong>Your personal 20% discount code:</strong> <code>TCRCOLLECTOR20</code>
    </p>
    <p>
        Use it at checkout on our website <a href="https://www.thecollectroom.com/" target="_blank">https://www.thecollectroom.com/</a> or our store "<em>The Collect Room,Dubai Hills Mall</em>" to expand your collection at a special rate.
    </p>
    <p>Happy collecting,<br><strong >The TCR Team</strong></p>
    """

    mail.send(msg)

    flash("Thank you for joining! Your 20% discount email has been sent.", "success")
    return redirect(request.referrer or url_for('home'))


# @app.route('/videos')
# def all_videos():
#     videos = YouTubeVideo.query.order_by(YouTubeVideo.id.desc()).all()
#     return render_template('all_videos.html', videos=videos)
@app.route('/videos')
def all_videos():
    shorts = YouTubeVideo.query.filter_by(is_short=True).order_by(YouTubeVideo.id.desc()).all()
    full_videos = YouTubeVideo.query.filter_by(is_short=False).order_by(YouTubeVideo.id.desc()).all()
    return render_template('all_videos.html', shorts=shorts, full_videos=full_videos)

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





