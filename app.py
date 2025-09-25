import datetime  # instead of "from datetime import datetime, timedelta"
import os
from datetime import datetime, timedelta
from flask import session
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
from googleapiclient.discovery import build
import isodate
from flask_mail import Mail, Message
import requests


load_dotenv()

app = Flask(__name__)

# Create instance folder if needed
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

today = datetime.now().date()



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
# app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Limit max upload size (e.g., 50MB)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB


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
    summary = db.Column(db.String(300))

    @property
    def image_url(self):
        if self.image_filename:
            return f"/static/uploads/{self.image_filename}"
        else:
            return "/static/uploads/default-placeholder.png"

class TopPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sport = db.Column(db.String(50), nullable=False)   # e.g., Football, Basketball, F1 Driver, Cricket
    rank = db.Column(db.Integer, nullable=False)
    player_name = db.Column(db.String(150), nullable=False)
    club = db.Column(db.String(150))  # e.g., 2025 club/team
    nationality = db.Column(db.String(100))
    sources = db.Column(db.String(255))  # comma-separated
    credits = db.Column(db.String(255))  # image/video credit

class TopFighter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sport = db.Column(db.String(50), nullable=False)   # e.g., Football, Basketball, F1 Driver, Cricket
    rank = db.Column(db.Integer, nullable=False)
    player_name = db.Column(db.String(150), nullable=False)
    club = db.Column(db.String(150))  # e.g., 2025 club/team
    nationality = db.Column(db.String(100))
    sources = db.Column(db.String(255))  # comma-separated
    credits = db.Column(db.String(255))  # image/video credit


class FootballTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league = db.Column(db.String(150), nullable=False)   # e.g., Premier League, Serie A
    rank = db.Column(db.Integer, nullable=False)
    team_name = db.Column(db.String(150), nullable=False)
    played = db.Column(db.Integer, default=0)
    won = db.Column(db.Integer, default=0)
    draw = db.Column(db.Integer, default=0)
    lost = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)


class CricketRanking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # 'odi', 'test', 't20', 'ipl'
    rank = db.Column(db.Integer, nullable=False)
    team_name = db.Column(db.String(150), nullable=False)
    matches = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    rating = db.Column(db.Integer, default=0)

class Formula1Ranking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  
    rank = db.Column(db.Integer, nullable=False)
    driver_name = db.Column(db.String(150), nullable=False)
    won = db.Column(db.Integer, default=0)
    podiums = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)

class BoxingRanking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False) 
    rank = db.Column(db.Integer, nullable=False)
    boxer_name = db.Column(db.String(150), nullable=False)
    titles = db.Column(db.String(350), nullable=False)

class MmaRanking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False) 
    rank = db.Column(db.Integer, nullable=False)
    fighter_name = db.Column(db.String(150), nullable=False)
    division = db.Column(db.String(350), nullable=False)    

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

class CollectibleStory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(300))
    image_url = db.Column(db.String(512)) 
    image_filename = db.Column(db.String(255))
    image_credit = db.Column(db.String(100))
    date = db.Column(db.String(50))
    content = db.Column(db.Text)
    
    likes = db.Column(db.Integer, default=0)  # start at 0

    def __repr__(self):
        return f"<CollectibleStory {self.title}>"

    @property
    def display_image(self):
        if self.image_filename:
            return f"/static/uploads/{self.image_filename}"
        elif self.image_url:
            return self.image_url
        else:
            return "/static/uploads/default-placeholder.png"

        
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

# --- Advertisement model in videos section ---
class ArenaplayAdvertisement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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


# Cricket Match Model
class CricketMatchDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    line1 = db.Column(db.String(255))
    line2 = db.Column(db.String(255))
    line3 = db.Column(db.String(255))
    line4 = db.Column(db.String(255))
    line5 = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)

# Basketball Match Model
class BasketballMatchDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    line1 = db.Column(db.String(255))
    line2 = db.Column(db.String(255))
    line3 = db.Column(db.String(255))
    line4 = db.Column(db.String(255))
    line5 = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)

# formula1 Match Model
class Formula1MatchDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    line1 = db.Column(db.String(255))
    line2 = db.Column(db.String(255))
    line3 = db.Column(db.String(255))
    line4 = db.Column(db.String(255))
    line5 = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)

# Boxing Match Model
class BoxingMatchDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    line1 = db.Column(db.String(255))
    line2 = db.Column(db.String(255))
    line3 = db.Column(db.String(255))
    line4 = db.Column(db.String(255))
    line5 = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)

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

# Cricket Admin Panel
class CricketMatchDetailAdmin(ModelView):
    column_list = ('title', 'line1', 'line2', 'line3', 'line4', 'line5', 'active')
    form_columns = ('title', 'line1', 'line2', 'line3', 'line4', 'line5', 'active')
    column_sortable_list = ('title', 'active')
    column_searchable_list = ('title', 'line1', 'line2', 'line3', 'line4', 'line5')
    page_size = 20

    def is_accessible(self):
        return current_user.is_authenticated

admin.add_view(CricketMatchDetailAdmin(CricketMatchDetail, db.session))

# Basketball Admin Panel
class BasketballMatchDetailAdmin(ModelView):
    column_list = ('title', 'line1', 'line2', 'line3', 'line4', 'line5', 'active')
    form_columns = ('title', 'line1', 'line2', 'line3', 'line4', 'line5', 'active')
    column_sortable_list = ('title', 'active')
    column_searchable_list = ('title', 'line1', 'line2', 'line3', 'line4', 'line5')
    page_size = 20

    def is_accessible(self):
        return current_user.is_authenticated

admin.add_view(BasketballMatchDetailAdmin(BasketballMatchDetail, db.session))


class Formula1MatchDetailAdmin(ModelView):
    # Columns to display in the list view
    column_list = ('title', 'line1', 'line2', 'line3', 'line4', 'line5', 'active')

    # Columns available in the add/edit form
    form_columns = ('title', 'line1', 'line2', 'line3', 'line4', 'line5', 'active')

    # Columns you can sort by
    column_sortable_list = ('title', 'active')

    # Columns searchable in the admin list view
    column_searchable_list = ('title', 'line1', 'line2', 'line3', 'line4', 'line5')

    # Pagination size
    page_size = 20

    # Only allow access to authenticated users
    def is_accessible(self):
        return current_user.is_authenticated
    
admin.add_view(Formula1MatchDetailAdmin(Formula1MatchDetail, db.session))

# Boxing Admin Panel
class BoxingMatchDetailAdmin(ModelView):
    column_list = ('title', 'line1', 'line2', 'line3', 'line4', 'line5', 'active')
    form_columns = ('title', 'line1', 'line2', 'line3', 'line4', 'line5', 'active')
    column_sortable_list = ('title', 'active')
    column_searchable_list = ('title', 'line1', 'line2', 'line3', 'line4', 'line5')
    page_size = 20

    def is_accessible(self):
        return current_user.is_authenticated

admin.add_view(BoxingMatchDetailAdmin(BoxingMatchDetail, db.session))

class TopPlayerAdmin(ModelView):
    column_list = ('sport', 'rank', 'player_name', 'club', 'nationality', 'sources')
    form_columns = ('sport', 'rank', 'player_name', 'club', 'nationality', 'sources')
    column_sortable_list = ('rank', 'sport', 'player_name')
    column_searchable_list = ('player_name', 'club', 'nationality')
    page_size = 20

    def is_accessible(self):
        return current_user.is_authenticated

admin.add_view(TopPlayerAdmin(TopPlayer, db.session))

class TopFighterAdmin(ModelView):
    column_list = ('sport', 'rank', 'player_name', 'club', 'nationality', 'sources', 'credits')
    form_columns = ('sport', 'rank', 'player_name', 'club', 'nationality', 'sources', 'credits')
    column_sortable_list = ('rank', 'sport', 'player_name')
    column_searchable_list = ('player_name', 'club', 'nationality')
    page_size = 20

    def is_accessible(self):
        return current_user.is_authenticated

admin.add_view(TopFighterAdmin(TopFighter, db.session))

class FootballTableAdmin(ModelView):
    column_list = ('league', 'rank', 'team_name', 'played', 'won', 'draw', 'lost', 'points')
    form_columns = ('league', 'rank', 'team_name', 'played', 'won', 'draw', 'lost', 'points')
    column_sortable_list = ('league', 'rank', 'team_name', 'points')
    column_searchable_list = ('league', 'team_name')
    
    def is_accessible(self):
        return current_user.is_authenticated


class CricketRankingAdmin(ModelView):
    column_list = ('type', 'rank', 'team_name', 'matches', 'points', 'rating')
    form_columns = ('type', 'rank', 'team_name', 'matches', 'points', 'rating')
    column_sortable_list = ('type', 'rank', 'team_name', 'points')
    column_searchable_list = ('type', 'team_name')

    def is_accessible(self):
        return current_user.is_authenticated

class Formula1RankingAdmin(ModelView):
    column_list = ('type', 'rank', 'driver_name', 'won', 'points', 'podiums')
    form_columns = ('type', 'rank', 'driver_name', 'won', 'points', 'podiums')
    column_sortable_list = ('type', 'rank', 'driver_name', 'points')
    column_searchable_list = ('type', 'driver_name')

    def is_accessible(self):
        return current_user.is_authenticated    
    

class BoxingRankingAdmin(ModelView):
    column_list = ('type', 'rank', 'boxer_name', 'titles')
    form_columns = ('type', 'rank', 'boxer_name', 'titles')
    column_sortable_list = ('type', 'rank', 'boxer_name', 'titles')
    column_searchable_list = ('type', 'boxer_name')

    def is_accessible(self):
        return current_user.is_authenticated    

class MmaRankingAdmin(ModelView):
    column_list = ('type', 'rank', 'fighter_name', 'division')
    form_columns = ('type', 'rank', 'fighter_name', 'division')
    column_sortable_list = ('type', 'rank', 'fighter_name', 'division')
    column_searchable_list = ('type', 'fighter_name')

    def is_accessible(self):
        return current_user.is_authenticated    
    
# Add to admin
admin.add_view(FootballTableAdmin(FootballTable, db.session))
admin.add_view(CricketRankingAdmin(CricketRanking, db.session))
admin.add_view(Formula1RankingAdmin(Formula1Ranking, db.session))
admin.add_view(BoxingRankingAdmin(BoxingRanking, db.session))
admin.add_view(MmaRankingAdmin(MmaRanking, db.session))

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

class CollectibleStoryAdmin(ModelView):
    upload_path = os.path.join(os.path.dirname(__file__), 'static/uploads')

    form_extra_fields = {
        'image_filename': FileUploadField(
            'Upload Image',
            base_path=upload_path,
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
            namegen=lambda obj, file_data: secure_filename(file_data.filename)
        )
    }

    column_list = ('id', 'title', 'subtitle', 'image_credit', 'date', 'likes', 'image_filename', 'image_url')
    column_searchable_list = ['title', 'image_credit']
    column_filters = ['image_credit', 'date']
    form_columns = ['title', 'subtitle', 'image_credit', 'date', 'likes', 'image_filename', 'image_url', 'content']

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
        'image_url': _list_thumbnail,
    }

    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin.add_view(CollectibleStoryAdmin(CollectibleStory, db.session))

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

# --- Advertisement admin view ---
class ArenaplayAdvertisementAdmin(ModelView):
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

    column_list = ('id', 'active', 'start_date', 'end_date', 'image_filename', 'image_url', 'video_filename', 'video_url')
    form_columns = ['active', 'start_date', 'end_date', 'image_filename', 'image_url', 'video_filename', 'video_url']

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
admin.add_view(ArenaplayAdvertisementAdmin(ArenaplayAdvertisement, db.session))
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
API_KEY = "538e881e9f4c4cb1d74708ddd91c6aa4"

LEAGUE_IDS = {
    "England: Premier League": 1204,
    "La Liga": 1399,
    "Serie A": 1269,
    "Germany: Bundesliga": 1014,
    "UEFA Champions League": 1005,
    "Saudi Pro League": 1368,
    # "Bhutan: Premier League": 18915,
    # "India: Calcutta Premier Division - Relegation Group": 4426
}

def fetch_matches():
    """Fetch live matches or nearest upcoming matches if no live matches exist"""
    live_matches = []
    upcoming_matches = []
    now = datetime.now()
    print("Current time =", now)

    try:
        live_url = f"http://www.goalserve.com/getfeed/{API_KEY}/soccernew/live?json=1"
        resp = requests.get(live_url, timeout=10)
        data = resp.json()
        categories = data.get("scores", {}).get("category", [])
        if isinstance(categories, dict):
            categories = [categories]

        for category in categories:
            league_name = category.get("@name", "")
            if league_name not in LEAGUE_IDS:
                continue
            matches_data = category.get("matches", {}).get("match", [])
            if isinstance(matches_data, dict):
                matches_data = [matches_data]

            for match in matches_data:
                date_str = match.get("@date")
                time_str = match.get("@time", "00:00")
                try:
                    match_dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
                except:
                    match_dt = now

                status_raw = match.get("@status", "").upper()
                status = "live" if status_raw == "LIVE" or (match_dt <= now < match_dt + timedelta(hours=2)) \
                         else ("past" if match_dt < now else "upcoming")

                match_obj = {
                    "league": league_name,
                    "home": match.get("localteam", {}).get("@name", ""),
                    "away": match.get("visitorteam", {}).get("@name", ""),
                    "score_home": match.get("localteam", {}).get("@goals") \
                                  or match.get("localteam", {}).get("@score") or "-",
                    "score_away": match.get("visitorteam", {}).get("@goals") \
                                  or match.get("visitorteam", {}).get("@score") or "-",
                    "status": status,
                    "timer": match.get("@timer", ""),
                    "time": time_str,
                    "date": date_str,
                    "venue": match.get("@venue", "")
                }

                if status == "live":
                    live_matches.append(match_obj)
                elif status == "upcoming":
                    upcoming_matches.append(match_obj)

    except Exception as e:
        print("Error fetching live matches:", e)

    # 2️⃣ Return live matches if they exist
    if live_matches:
        return live_matches

    # 3️⃣ No live matches → return nearest upcoming matches
    if upcoming_matches:
        # Optional: sort upcoming matches to get nearest ones first
        upcoming_matches.sort(key=lambda x: datetime.strptime(f"{x['date']} {x['time']}", "%d.%m.%Y %H:%M"))
        return upcoming_matches[:5]  # return top 5 upcoming matches

    # 4️⃣ No live or upcoming matches → fallback to league list
    return [{"league": name} for name in LEAGUE_IDS.keys()]


# Cricket Match API
@app.route("/cricketmatch-details")
def cricketmatch_details():
    details = CricketMatchDetail.query.filter_by(active=True).order_by(CricketMatchDetail.id.desc()).all()
    if details:
        return jsonify([
            {
                "title": d.title,
                "lines": [d.line1, d.line2, d.line3, d.line4, d.line5]
            }
            for d in details
        ])
    else:
        return jsonify([])

# Basketball Match API
@app.route("/basketballmatch-details")
def basketballmatch_details():
    details = BasketballMatchDetail.query.filter_by(active=True).order_by(BasketballMatchDetail.id.desc()).all()
    if details:
        return jsonify([
            {
                "title": d.title,
                "lines": [d.line1, d.line2, d.line3, d.line4, d.line5]
            }
            for d in details
        ])
    else:
        return jsonify([])


# Formula1 Match API

@app.route("/formula1match-details")
def formula1match_details():
    details = Formula1MatchDetail.query.filter_by(active=True).order_by(Formula1MatchDetail.id.desc()).all()
    if details:
        return jsonify([
            {
                "title": d.title,
                "lines": [d.line1, d.line2, d.line3, d.line4, d.line5]
            }
            for d in details
        ])
    else:
        return jsonify([])


# Boxing Match API
@app.route("/boxingmatch-details")
def boxingmatch_details():
    details = BoxingMatchDetail.query.filter_by(active=True).order_by(BoxingMatchDetail.id.desc()).all()
    if details:
        return jsonify([
            {
                "title": d.title,
                "lines": [d.line1, d.line2, d.line3, d.line4, d.line5]
            }
            for d in details
        ])
    else:
        return jsonify([])

    
@app.route("/matches")
def matches_by_date():
    date_query = request.args.get("date")
    selected_league = request.args.get("league")
    now = datetime.now()

    # Use the query date if provided, otherwise consider today
    selected_dt = datetime.strptime(date_query, "%d.%m.%Y") if date_query else now

    all_matches = []
    upcoming_matches = []

    for league_name, league_id in LEAGUE_IDS.items():
        if selected_league and selected_league != league_name:
            continue

        url = f"https://www.goalserve.com/getfeed/{API_KEY}/soccerfixtures/leagueid/{league_id}?json=1"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results") or {}
            tournament = results.get("tournament") or {}
            weeks = tournament.get("week") or []
            if isinstance(weeks, dict):
                weeks = [weeks]

            for week in weeks:
                week = week or {}
                matches = week.get("match") or []
                if isinstance(matches, dict):
                    matches = [matches]

                for match in matches:
                    match_date_str = match.get("@date")
                    match_time_str = match.get("@time", "00:00")
                    if not match_date_str:
                        continue
                    try:
                        match_dt = datetime.strptime(f"{match_date_str} {match_time_str}", "%d.%m.%Y %H:%M")
                    except:
                        continue

                    # Filter by date if provided
                    if date_query and match_dt.date() != selected_dt.date():
                        # Keep for upcoming fallback
                        if match_dt > now:
                            match["league"] = league_name
                            upcoming_matches.append(match)
                        continue

                    # Filter out past matches if no date query
                    if not date_query and match_dt < now:
                        continue

                    match["league"] = league_name

                    # Process events (goals, bookings, substitutions)
                    events = []

                    # Goals
                    goals_data = (match.get("goals") or {}).get("goal") or []
                    if isinstance(goals_data, dict):
                        goals_data = [goals_data]
                    for g in goals_data:
                        events.append({
                            "type": "goal",
                            "team": g.get("@team"),
                            "player": g.get("@player"),
                            "minute": g.get("@minute"),
                            "assist": g.get("@assist"),
                            "score": g.get("@score")
                        })

                    # Bookings
                    for side in ["localteam", "visitorteam"]:
                        lineup = ((match.get("lineups") or {}).get(side) or {}).get("player") or []
                        if isinstance(lineup, dict):
                            lineup = [lineup]
                        for p in lineup:
                            booking = p.get("@booking")
                            if booking:
                                events.append({
                                    "type": "booking",
                                    "team": side,
                                    "player": p.get("@name"),
                                    "minute": booking.split(" ")[-1]
                                })

                    # Substitutions
                    for side in ["localteam", "visitorteam"]:
                        subs = ((match.get("substitutions") or {}).get(side) or {}).get("substitution") or []
                        if isinstance(subs, dict):
                            subs = [subs]
                        for s in subs:
                            events.append({
                                "type": "substitution",
                                "team": side,
                                "player_in": s.get("@player_in_name"),
                                "player_out": s.get("@player_out_name"),
                                "minute": s.get("@minute")
                            })

                    match["events"] = events
                    all_matches.append(match)

            # Sort matches by datetime
            all_matches.sort(
                key=lambda x: datetime.strptime(
                    f"{x.get('@date','01.01.1970')} {x.get('@time','00:00')}", "%d.%m.%Y %H:%M"
                )
            )

        except Exception as e:
            print(f"Error fetching {league_name}: {e}")

    # If no matches found for selected date, return nearest upcoming matches
    if date_query and not all_matches and upcoming_matches:
        upcoming_matches.sort(key=lambda x: datetime.strptime(
            f"{x.get('@date','01.01.1970')} {x.get('@time','00:00')}", "%d.%m.%Y %H:%M"
        ))
        all_matches = upcoming_matches[:5]  # top 5 nearest matches

    return jsonify(all_matches)


@app.route('/all-scores',methods=["GET"])
def all_scores():
    matches = fetch_matches()
    return render_template("all_scores.html", matches=matches)

@app.route('/top-players-json')
def top_players_json():
    sport = request.args.get('sport', '').strip()
    if not sport:
        return jsonify({"players": []})

    players = TopPlayer.query.filter_by(sport=sport).order_by(TopPlayer.rank).all()
    players_list = [{
        "rank": p.rank,
        "player_name": p.player_name,
        "club": p.club,
        "nationality": p.nationality,
        "sources": p.sources,
        "credits": p.credits
    } for p in players]

    return jsonify({"players": players_list})

@app.route('/top-fighters-json')
def top_fighters_json():
    sport = request.args.get('sport', '').strip()
    if not sport:
        return jsonify({"players": []})

    players = TopFighter.query.filter_by(sport=sport).order_by(TopFighter.rank).all()
    fighters_list = [{
        "rank": p.rank,
        "player_name": p.player_name,
        "club": p.club,
        "nationality": p.nationality,
        "sources": p.sources,
        "credits": p.credits
    } for p in players]

    return jsonify({"players": fighters_list})

@app.route('/football-tables')
def football_tables():
    league = request.args.get('league', '').strip()
    if not league:
        return jsonify({"teams": []})

    teams = FootballTable.query.filter_by(league=league).order_by(FootballTable.rank).all()

    teams_list = [{
        "rank": t.rank,
        "name": t.team_name,
        "played": t.played,
        "won": t.won,
        "draw": t.draw,
        "lost": t.lost,
        "points": t.points
    } for t in teams]

    return jsonify({"teams": teams_list})


@app.route('/cricket-rankings')
def cricket_rankings():
    ranking_type = request.args.get('type', '').strip()  # 'odi', 'test', 't20', 'ipl'
    if not ranking_type:
        return jsonify({"teams": []})

    teams = CricketRanking.query.filter_by(type=ranking_type).order_by(CricketRanking.rank).all()

    teams_list = [{
        "rank": t.rank,
        "name": t.team_name,
        "matches": t.matches,
        "points": t.points,
        "rating": t.rating
    } for t in teams]

    return jsonify({"teams": teams_list})

@app.route('/formula1-rankings')
def formula1_tables():
    ranking_type = request.args.get('type', '').strip()
    if not ranking_type:
        return jsonify({"teams": []})

    drivers = Formula1Ranking.query.filter_by(type=ranking_type).order_by(Formula1Ranking.rank).all()

    drivers_list = [{
        "rank": d.rank,
        "driver_name": d.driver_name,
        "won": d.won,
        "podiums": d.podiums,
        "points": d.points
    } for d in drivers]

    return jsonify({"teams": drivers_list})


@app.route('/boxing-rankings')
def boxing_tables():
    ranking_type = request.args.get('type', '').strip()
    if not ranking_type:
        return jsonify({"teams": []})

    boxers = BoxingRanking.query.filter_by(type=ranking_type).order_by(BoxingRanking.rank).all()

    boxers_list = [{
        "rank": d.rank,
        "boxer_name": d.boxer_name,
        "titles": d.titles
    } for d in boxers]

    return jsonify({"teams": boxers_list})


@app.route('/mma-rankings')
def mma_tables():
    ranking_type = request.args.get('type', '').strip()
    if not ranking_type:
        return jsonify({"teams": []})

    fighters = MmaRanking.query.filter_by(type=ranking_type).order_by(MmaRanking.rank).all()

    fighters_list = [{
        "rank": d.rank,
        "fighter_name": d.fighter_name,
        "division": d.division,
    } for d in fighters]

    return jsonify({"teams": fighters_list})

# --- TCR Home Page ---
@app.route('/')
def home():
    matches = fetch_matches()
    news_items = News.query.order_by(News.id.desc()).limit(6).all()
    products = Product.query.order_by(Product.id.desc()).limit(5).all()
    memorabilia_stories = MemorabiliaStory.query.order_by(MemorabiliaStory.id.desc()).limit(6).all()
    # Separate videos and images
    videos = [s for s in memorabilia_stories if s.display_video][:2]   # max 2 videos
    images = [s for s in memorabilia_stories if not s.display_video][:4]  # max 4 images

    # Final mix for grid
    collectors_items = videos + images
    youtube_shorts = YouTubeVideo.query.filter_by(is_short=True).order_by(YouTubeVideo.id.desc()).limit(5).all()
    ad = Advertisement.query.filter_by(active=True).order_by(Advertisement.id.desc()).first()
    welcome_text = "Welcome to TCR Arena - your hub for sports insights, collectibles and exclusive content!"
    return render_template(
        'index.html',
        news_items=news_items,
        products=products,
        # memorabilia_stories=memorabilia_stories,
        memorabilia_stories=collectors_items, 
        youtube_videos=youtube_shorts,
        advertisement=ad,
        welcome_text=welcome_text,
        matches=matches
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
#     videos_per_page = 4
#     images_per_page = 6

#     # Fetch all items ordered by date
#     all_items = MemorabiliaStory.query.order_by(MemorabiliaStory.date.desc()).all()
#     all_videos = [item for item in all_items if item.display_video]
#     all_images = [item for item in all_items if not item.display_video]

#     # Sort images by id
#     all_images.sort(key=lambda x: x.id, reverse=True)
#     all_videos.sort(key=lambda x: x.id, reverse=True)

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
@app.route('/memorabilia')
def memorabilia():
    page = request.args.get('page', 1, type=int)
    videos_per_page = 4
    images_per_page = 6

    # Memorabilia stories
    all_items = MemorabiliaStory.query.order_by(MemorabiliaStory.date.desc()).all()
    all_videos = [item for item in all_items if item.display_video]
    all_images = [item for item in all_items if not item.display_video]
    all_images.sort(key=lambda x: x.id, reverse=True)
    all_videos.sort(key=lambda x: x.id, reverse=True)

    video_start = (page - 1) * videos_per_page
    video_end = video_start + videos_per_page
    image_start = (page - 1) * images_per_page
    image_end = image_start + images_per_page

    videos = all_videos[video_start:video_end]
    images = all_images[image_start:image_end]

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

    # Collectible stories for "Collectible Stories" tab
    collectible_stories = CollectibleStory.query.order_by(CollectibleStory.date.desc()).all()

    # Collector videos for carousel
    collector_videos = CollectorVideo.query.order_by(CollectorVideo.date.desc()).limit(10).all()

    return render_template(
        'memorabilia.html',
        videos=videos,
        images=images,
        pagination=pagination,
        memorabilia_stories=videos + images,
        collector_videos=collector_videos,
        collectible_stories=collectible_stories
    )

@app.route('/collectible/<int:item_id>')
def view_collectible(item_id):
    item = CollectibleStory.query.get_or_404(item_id)
    suggestions = CollectibleStory.query.filter(
        CollectibleStory.id != item_id
    ).order_by(CollectibleStory.id.desc()).limit(3).all()
    
    return render_template(
        'memorabilia_detail.html',
        item=item,
        suggestions=suggestions
    )


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

@app.route('/like/collectible/<int:item_id>', methods=['POST'])
def like_collectible(item_id):
    item = CollectibleStory.query.get(item_id)
    if not item:
        return {"error": "Item not found"}, 404

    # Track liked collectibles in session
    liked_items = session.get('liked_collectibles', [])

    if item_id in liked_items:
        return {"error": "Already liked"}, 400

    if item.likes is None:
        item.likes = 0

    item.likes += 1
    db.session.commit()

    liked_items.append(item_id)
    session['liked_collectibles'] = liked_items

    return {"likes": item.likes}


# Titan SMTP config
app.config['MAIL_SERVER'] = 'smtp.titan.email'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "digital@thecollectroom.com"   # your Titan email
app.config['MAIL_PASSWORD'] = "ESC@2025"                   # Titan password
app.config['MAIL_DEFAULT_SENDER'] = "digital@thecollectroom.com"

mail = Mail(app)

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
            new_contact = Contact(
                name=name,
                email=email,
                contact_number=contact_number,
                message=message
            )
            db.session.add(new_contact)
            db.session.commit()

            # --- Send Email ---
            try:
                msg = Message(
                    subject="New Contact Form Submission - TCR Arena",
                    recipients=["digital@thecollectroom.com"]
                )

                # Plain text fallback (always good to have)
                msg.body = f"""
                A new contact form submission has been received:

                Name: {name}
                Email: {email}
                Contact Number: {contact_number}
                Message: {message}
                """

                # HTML version with styling
                msg.html = f"""
                <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color:#054a9a;">New Contact Form Submission - TCR Arena</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Contact Number:</strong> {contact_number}</p>
                <p><strong>Message:</strong></p>
                <div style="text-align: justify; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #f9f9f9;">
                    {message}
                </div>
                <hr>
                <p style="font-size:12px; color:#777;">This email was automatically generated by TCR Arena.</p>
                </div>
                """

                mail.send(msg)
            except Exception as e:
                app.logger.error(f"Failed to send email: {e}")

            session['joined'] = True
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
#     shorts = YouTubeVideo.query.filter_by(is_short=True).order_by(YouTubeVideo.id.desc()).all()
#     full_videos = YouTubeVideo.query.filter_by(is_short=False).order_by(YouTubeVideo.id.desc()).all()
#     return render_template('all_videos.html', shorts=shorts, full_videos=full_videos)


YOUTUBE_API_KEY = 'AIzaSyDg4UvVFz06U-64ydsG_gC3_qkN8sntrLU'
CHANNEL_ID = 'UCjr5E_A1k7cKaTcvGjjl44A'

# Playlist containing all Shorts videos
SHORTS_PLAYLIST_ID = 'PLgsIMVkeMYCwFXqG8U39kXyN0WtGFM40l'

# Playlist containing all full-length videos (main uploads or custom playlist)
FULL_PLAYLIST_ID = 'PLgsIMVkeMYCwd2MlJum2Y0UMY6d-UfhR6'

def fetch_videos_from_playlist(playlist_id):
    """Fetch all videos from a given YouTube playlist."""
    videos = []
    url = 'https://www.googleapis.com/youtube/v3/playlistItems'
    params = {
        'key': YOUTUBE_API_KEY,
        'playlistId': playlist_id,
        'part': 'snippet',
        'maxResults': 50
    }

    while True:
        response = requests.get(url, params=params).json()
        items = response.get('items', [])

        for item in items:
            snippet = item['snippet']
            video_id = snippet['resourceId']['videoId']
            title = snippet['title']

            videos.append({
                'video_id': video_id,
                'title': title
            })

        if 'nextPageToken' in response:
            params['pageToken'] = response['nextPageToken']
        else:
            break

    return videos


@app.route('/videos')
def all_videos():
    # Fetch YouTube Shorts + Full videos
    shorts = fetch_videos_from_playlist(SHORTS_PLAYLIST_ID)
    full_videos = fetch_videos_from_playlist(FULL_PLAYLIST_ID)

    # TikTok username to embed
    tiktok_username = "thecollectroom"

    # Fetch active advertisement
    apad = ArenaplayAdvertisement.query.filter_by(active=True).order_by(ArenaplayAdvertisement.id.desc()).first()

    # Collector videos for carousel
    collector_videos = CollectorVideo.query.order_by(CollectorVideo.date.desc()).limit(10).all()

    return render_template(
        'all_videos.html',
        shorts=shorts,
        full_videos=full_videos,
        tiktok_username=tiktok_username,
        arenaplayadvertisement=apad,
        collector_videos=collector_videos
    )


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





