import re
from flask import Flask, Response, render_template, request, redirect, url_for, session, g, abort, jsonify, flash
from translations import translate
from flask_mail import Mail, Message
from flask_migrate import Migrate
import os
import uuid
import json
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from firebase_admin import auth
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
import cloudinary
import cloudinary.uploader
from functools import wraps



load_dotenv()

app = Flask(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

cred_path = os.environ.get(
    "FIREBASE_CRED_PATH",
    "./mediamission-a0b70-firebase-adminsdk-fbsvc-a1ebbce726.json"
)

cred = credentials.Certificate(cred_path)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

print("Firebase initialized!")


# 1. СПОЧАТКУ задаємо налаштування бази даних:
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///mediamission.db").replace("postgres://", "postgresql://", 1)  # Render іноді дає старий префікс
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32).hex()) # Потрібно для Flask-Admin

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
# os.getenv повертає рядок, тому для bool робимо перевірку:
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('MediaMission', os.getenv('MAIL_USERNAME'))

mail = Mail(app)

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# 2. І ТІЛЬКИ ПОТІМ передаємо app у SQLAlchemy:
db = SQLAlchemy(app)

# Створення колонок бази данних для місій
class Missions(db.Model):
    __tablename__ = "missions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)
    exercise = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(30), nullable=False)
    difficulty = db.Column(db.String(30), nullable=False)
    xp = db.Column(db.Integer, nullable=False)
    time = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(300))
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # Зв'язки (1 -> Багато)
    contents = db.relationship(
        "MissionContent", 
        backref="mission", 
        lazy=True, 
        cascade="all, delete-orphan",
        order_by="MissionContent.paragraph_order"  # Сортування контенту за порядком
    )
    
    questions = db.relationship(
        "Questions", 
        backref="mission", 
        lazy=True, 
        cascade="all, delete-orphan"
    )

class MissionContent(db.Model):
    __tablename__ = "mission_contents"

    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(
        db.Integer,
        db.ForeignKey("missions.id"),
        nullable=False
    )
    paragraph_order = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)

class Questions(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(
        db.Integer,
        db.ForeignKey("missions.id"),
        nullable=False
    )
    type = db.Column(db.String(30))
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(300), nullable=False)

    # Зв'язок з варіантами відповідей (1 -> Багато)
    options = db.relationship(
        "Options", 
        backref="question", 
        lazy=True, 
        cascade="all, delete-orphan",
        order_by="Options.option_order"  # Сортування варіантів за порядком
    )

class Options(db.Model):
    __tablename__ = "options"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id"),
        nullable=False
    )
    option_order = db.Column(db.Integer, nullable=False)
    option_text = db.Column(db.Text, nullable=False)

#Створення колонок бази данних для інфи користувача
class Users(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(300), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(300), nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    provider = db.Column(db.String(30), nullable=False, default="password")
    total_xp = db.Column(db.Integer, default=0)
    missions_completed = db.Column(db.Integer, default=0)
    accuracy = db.Column(db.Float, default=0)
    streak = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime)
    admin = db.Column(db.Boolean, default=False)
    allowed_to_show = db.Column(db.Boolean, default=True, nullable=False)
    avatar = db.Column(db.String(500), nullable=True)
    photo_url = db.Column(db.String(500))
    language = db.Column(db.String(70), default="uk")

class SecureAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for('login'))
        user = db.session.get(Users, user_id)
        if not user or not user.admin:
            return "Forbidden", 403
        return super().index()

class SecureModelView(ModelView):
    def is_accessible(self):
        user_id = session.get("user_id")
        if not user_id:
            return False
        user = db.session.get(Users, user_id)
        return user is not None and user.admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class UserAdminView(SecureModelView):
    column_searchable_list = ['email']
    column_list = ['id', 'email']

# 3. Ініціалізація адмінки
admin = Admin(app, name='MediaMission Admin', index_view=SecureAdminIndexView())

# 4. РЕЄСТРАЦІЯ МОДЕЛІ (Обов'язково викликати!)
admin.add_view(UserAdminView(Users, db))

class UserMissionProgress(db.Model):
    __tablename__ = "user_mission_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    mission_id = db.Column(
        db.Integer,
        db.ForeignKey("missions.id"),
        nullable=False
    )
    completed = db.Column(db.Boolean, default=False)
    score_correct_answers = db.Column(db.Integer)
    total_questions = db.Column(db.Integer)
    xp_earned = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime)
    tries_number = db.Column(db.Integer, default=1)
    time_spent = db.Column(db.Integer)
    mission = db.relationship("Missions")

class UserAnswer(db.Model):
    __tablename__ = "user_answers"

    id = db.Column(db.Integer, primary_key=True)
    user_progress_id = db.Column(
        db.Integer,
        db.ForeignKey("user_mission_progress.id"),
        nullable=False
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id"),
        nullable=False
    )
    user_answer = db.Column(db.String(700), nullable=False)
    is_correct = db.Column(db.Boolean)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=True)
    mission = db.relationship("Missions")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

class NotificationRecipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("notification.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)

    notification = db.relationship("Notification")  # тепер n.notification.title працює

class Achievement(db.Model):
    """Таблиця з усіма можливими досягненнями"""
    __tablename__ = "achievements"
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)  # унікальний ключ
    title_uk = db.Column(db.String(200), nullable=False)
    title_de = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200), nullable=False)
    description_uk = db.Column(db.String(500), nullable=False)
    description_de = db.Column(db.String(500), nullable=False)
    description_en = db.Column(db.String(500), nullable=False)
    icon = db.Column(db.String(50), nullable=False)  # клас іконки Bootstrap
    category = db.Column(db.String(50), default='general')  # missions, xp, streak, etc.
    xp_reward = db.Column(db.Integer, default=0)  # бонусні XP за досягнення
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Зв'язок з користувачами
    user_achievements = db.relationship("UserAchievement", backref="achievement", lazy=True, cascade="all, delete-orphan")


class UserAchievement(db.Model):
    """Таблиця для зв'язку користувачів з досягненнями"""
    __tablename__ = "user_achievements"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey("achievements.id"), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_new = db.Column(db.Boolean, default=True)  # для показу сповіщення про нове досягнення
    
    # Унікальність: один користувач може мати одне досягнення один раз
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='unique_user_achievement'),)
    
    # Зв'язки
    user = db.relationship("Users", backref=db.backref("user_achievements", lazy=True, cascade="all, delete-orphan"))


UKRAINIAN_MONTHS = [
    "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"
]

AVATAR_COLORS = [
    "#FF6B6B", "#F06595", "#CC5DE8", "#845EF7", "#5C7CFA",
    "#339AF0", "#22B8CF", "#20C997", "#51CF66", "#94D82D",
    "#FCC419", "#FF922B", "#FF8787", "#748FFC", "#63E6BE",
]

migrate = Migrate(app, db)


@app.before_request
def set_language():
    lang = None

    user_id = session.get("user_id")
    if user_id:
        user = Users.query.get(user_id)
        if user:
            lang = user.language

    if lang is None:
        lang = session.get("language", "uk")

    g.lang = lang

# Робимо функцію перекладу доступною напряму в усіх шаблонах
@app.context_processor
def inject_translate():
    return {"t": lambda key: translate(key, g.lang)}




def init_achievements():
    """Ініціалізація досягнень у базі даних"""
    achievements = [
        {
            'key': 'first_steps',
            'title_uk': 'Перші кроки',
            'title_de': 'Erste Schritte',
            'title_en': 'First Steps',
            'description_uk': 'Зареєструватися та завершити 1-шу місію',
            'description_de': 'Registrieren und die 1. Mission abschließen',
            'description_en': 'Register and complete your 1st mission',
            'icon': 'bi-flag-fill',
            'category': 'missions',
            'xp_reward': 10
        },
        {
            'key': 'fake_detective',
            'title_uk': 'Детектив фейків',
            'title_de': 'Fälschungsdetektiv',
            'title_en': 'Fake Detective',
            'description_uk': 'Розпізнати 5 маніпуляцій у новинах',
            'description_de': '5 Manipulationen in Nachrichten erkennen',
            'description_en': 'Spot 5 manipulations in news',
            'icon': 'bi-search',
            'category': 'missions',
            'xp_reward': 20
        },
        {
            'key': 'unbreakable_logic',
            'title_uk': 'Непробивна логіка',
            'title_de': 'Unerschütterliche Logik',
            'title_en': 'Unbreakable Logic',
            'description_uk': 'Отримати 1000 XP на платформі',
            'description_de': '1000 XP auf der Plattform erhalten',
            'description_en': 'Earn 1000 XP on the platform',
            'icon': 'bi-shield-check',
            'category': 'xp',
            'xp_reward': 50
        },
        {
            'key': 'streak_master',
            'title_uk': '🔥 Майстер серії',
            'title_de': '🔥 Serien-Meister',
            'title_en': '🔥 Streak Master',
            'description_uk': 'Досягти 7-денної серії',
            'description_de': '7-Tage-Serie erreichen',
            'description_en': 'Reach 7-day streak',
            'icon': 'bi-fire',
            'category': 'streak',
            'xp_reward': 30
        },
        {
            'key': 'xp_hunter',
            'title_uk': '🎯 Мисливець за XP',
            'title_de': '🎯 XP-Jäger',
            'title_en': '🎯 XP Hunter',
            'description_uk': 'Накопичити 5000 XP',
            'description_de': '5000 XP sammeln',
            'description_en': 'Accumulate 5000 XP',
            'icon': 'bi-target',
            'category': 'xp',
            'xp_reward': 100
        },
        {
            'key': 'mission_master',
            'title_uk': '🏆 Майстер місій',
            'title_de': '🏆 Missions-Meister',
            'title_en': '🏆 Mission Master',
            'description_uk': 'Пройди 25 місій',
            'description_de': '25 Missionen abschließen',
            'description_en': 'Complete 25 missions',
            'icon': 'bi-trophy',
            'category': 'missions',
            'xp_reward': 75
        },
        {
            'key': 'accuracy_expert',
            'title_uk': '🎯 Експерт точності',
            'title_de': '🎯 Genauigkeits-Experte',
            'title_en': '🎯 Accuracy Expert',
            'description_uk': 'Досягти 90% точності відповідей',
            'description_de': '90% Antwortgenauigkeit erreichen',
            'description_en': 'Reach 90% answer accuracy',
            'icon': 'bi-bullseye',
            'category': 'accuracy',
            'xp_reward': 40
        },
        {
            'key': 'media_literate',
            'title_uk': '📰 Медіаграмотний',
            'title_de': '📰 Medienkompetent',
            'title_en': '📰 Media Literate',
            'description_uk': 'Пройди місії всіх типів',
            'description_de': 'Missionen aller Typen abschließen',
            'description_en': 'Complete missions of all types',
            'icon': 'bi-newspaper',
            'category': 'missions',
            'xp_reward': 60
        },
        {
            'key': 'speedrunner',
            'title_uk': '⚡ Спринтер',
            'title_de': '⚡ Sprinter',
            'title_en': '⚡ Speedrunner',
            'description_uk': 'Пройди місію менш ніж за 30 секунд',
            'description_de': 'Mission in weniger als 30 Sekunden abschließen',
            'description_en': 'Complete a mission in under 30 seconds',
            'icon': 'bi-lightning',
            'category': 'speed',
            'xp_reward': 25
        },
        {
            'key': 'perfect_score',
            'title_uk': '💯 Ідеальний рахунок',
            'title_de': '💯 Perfekte Punktzahl',
            'title_en': '💯 Perfect Score',
            'description_uk': 'Отримати 100% на будь-якій місії',
            'description_de': '100% bei jeder Mission erreichen',
            'description_en': 'Get 100% on any mission',
            'icon': 'bi-stars',
            'category': 'accuracy',
            'xp_reward': 35
        }
    ]
    
    for ach_data in achievements:
        existing = Achievement.query.filter_by(key=ach_data['key']).first()
        if not existing:
            achievement = Achievement(**ach_data)
            db.session.add(achievement)
    
    db.session.commit()




def check_and_unlock_achievements(user_id):
    """Перевіряє та розблоковує досягнення для користувача"""
    user = Users.query.get(user_id)
    if not user:
        return []
    
    # Отримуємо всі досягнення користувача
    unlocked_achievements = set(
        ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user_id).all()
    )
    
    # Отримуємо всі можливі досягнення
    all_achievements = Achievement.query.all()
    
    newly_unlocked = []
    
    for achievement in all_achievements:
        # Пропускаємо вже розблоковані
        if achievement.id in unlocked_achievements:
            continue
        
        # Перевіряємо умови для кожного досягнення
        is_unlocked = False
        
        if achievement.key == 'first_steps':
            is_unlocked = user.missions_completed >= 1
        
        elif achievement.key == 'fake_detective':
            is_unlocked = user.missions_completed >= 5
        
        elif achievement.key == 'unbreakable_logic':
            is_unlocked = user.total_xp >= 1000
        
        elif achievement.key == 'streak_master':
            is_unlocked = user.streak >= 7
        
        elif achievement.key == 'xp_hunter':
            is_unlocked = user.total_xp >= 5000
        
        elif achievement.key == 'mission_master':
            is_unlocked = user.missions_completed >= 25
        
        elif achievement.key == 'accuracy_expert':
            is_unlocked = user.accuracy >= 90
        
        elif achievement.key == 'media_literate':
            # Перевіряємо, чи пройдені місії всіх типів
            completed_types = db.session.query(
                Missions.type
            ).join(
                UserMissionProgress, UserMissionProgress.mission_id == Missions.id
            ).filter(
                UserMissionProgress.user_id == user_id,
                UserMissionProgress.completed == True
            ).distinct().all()
            
            all_types = db.session.query(Missions.type).distinct().all()
            is_unlocked = set(t[0] for t in completed_types) == set(t[0] for t in all_types)
        
        elif achievement.key == 'speedrunner':
            # Перевіряємо, чи є місія пройдена менш ніж за 30 секунд
            fast_mission = UserMissionProgress.query.filter(
                UserMissionProgress.user_id == user_id,
                UserMissionProgress.completed == True,
                UserMissionProgress.time_spent < 30
            ).first()
            is_unlocked = fast_mission is not None
        
        elif achievement.key == 'perfect_score':
            # Перевіряємо, чи є місія з 100% правильних відповідей
            perfect_mission = UserMissionProgress.query.filter(
                UserMissionProgress.user_id == user_id,
                UserMissionProgress.completed == True,
                UserMissionProgress.score_correct_answers == UserMissionProgress.total_questions
            ).first()
            is_unlocked = perfect_mission is not None
        
        # Якщо досягнення розблоковано
        if is_unlocked:
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                unlocked_at=datetime.now(timezone.utc),
                is_new=True
            )
            db.session.add(user_achievement)
            newly_unlocked.append(achievement)
            
            # Додаємо бонусні XP за досягнення
            if achievement.xp_reward > 0:
                user.total_xp += achievement.xp_reward
    
    if newly_unlocked:
        db.session.commit()
    
    return newly_unlocked




def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None:
            return redirect(url_for("login"))

        user = db.session.get(Users, user_id)
        if user is None:
            session.clear()
            return redirect(url_for("login"))

        if not getattr(user, "admin", False):
            abort(403)

        return f(*args, **kwargs)
    return decorated




@app.route("/robots.txt")
def robots():
    return Response(
        f"""User-agent: *
Allow: /

Sitemap: {request.url_root}sitemap.xml
""",
        mimetype="text/plain"
    )




@app.route("/sitemap.xml")
def sitemap():

    pages = []

    # Статичні сторінки
    pages.append({
        "loc": url_for("index", _external=True),
        "priority": "1.0",
        "changefreq": "weekly"
    })

    pages.append({
        "loc": url_for("missions_overview", _external=True),
        "priority": "0.9",
        "changefreq": "daily"
    })

    pages.append({
        "loc": url_for("leaderboard", _external=True),
        "priority": "0.8",
        "changefreq": "daily"
    })

    pages.append({
        "loc": url_for("login", _external=True),
        "priority": "0.5",
        "changefreq": "monthly"
    })

    pages.append({
        "loc": url_for("register", _external=True),
        "priority": "0.5",
        "changefreq": "monthly"
    })

    # Усі місії
    for mission in Missions.query.all():
        pages.append({
            "loc": url_for("mission_detail", id=mission.id, _external=True),
            "priority": "0.9",
            "changefreq": "monthly"
        })

    xml = render_template(
        "sitemap.xml",
        pages=pages,
        lastmod=datetime.utcnow().date().isoformat()
    )

    return Response(xml, mimetype="application/xml")




@app.route("/api/privacy", methods=["POST"])
def update_privacy():

    user_id = session.get("user_id")
    if not user_id:
        return {"success": False}, 401

    data = request.get_json()
    user = db.session.get(Users, user_id)
    user.allowed_to_show = data["allowed_to_show"]

    db.session.commit()

    return {"success": True}




@app.route("/api/debug/fix_avatars/<secret>")
def fix_avatars(secret):
    if secret != os.environ.get("ADMIN_SETUP_SECRET"):
        return "Forbidden", 403

    users = Users.query.all()
    output = []

    for user in users:
        avatar_value = user.avatar
        is_valid = avatar_value and avatar_value.startswith("http")
        output.append(f"{user.display_name}: avatar={avatar_value!r}, valid={is_valid}")

        # Якщо це старий, невалідний запис — очищуємо
        if avatar_value and not is_valid:
            user.avatar = None

    db.session.commit()

    return "<br>".join(output)



@app.route("/api/set_language", methods=["POST"])
def set_language_api():
    data = request.get_json()
    lang = data.get("language")

    if lang not in ("uk", "de", "en"):
        return {"success": False, "error": "непідтримувана мова"}, 400

    session["language"] = lang

    user_id = session.get("user_id")
    if user_id:
        user = Users.query.get(user_id)
        if user:
            user.language = lang
            db.session.commit()

    return {"success": True}



@app.route("/set_language/<lang>")
def set_language_redirect(lang):
    if lang not in ("uk", "de", "en"):
        lang = "uk"

    session["language"] = lang

    user_id = session.get("user_id")
    if user_id:
        user = Users.query.get(user_id)
        if user:
            user.language = lang
            db.session.commit()

    # Повертаємо користувача туди, звідки він прийшов
    next_page = request.referrer or url_for('index')
    return redirect(next_page)




@app.template_filter('date_uk')
def date_uk(value):
    if value is None:
        return ""
    return f"{value.strftime('%H:%M')}, {value.day} {UKRAINIAN_MONTHS[value.month - 1]}"




@app.route("/")
def index():
    return render_template('index.html')




@app.route("/missions-overview")
def missions_overview():
    missions = Missions.query.all()
    return render_template('missions.html', missions=missions)





@app.route("/mission/<int:id>", methods=['GET', 'POST'])
def mission_detail(id):
    mission = Missions.query.get(id)
    if mission is None:
        return "Mission not found", 404

    user_id = session.get("user_id")
    if user_id is not None and Users.query.get(user_id) is None:
        session.clear()
        user_id = None

    if request.method == 'POST':
        started_at = request.form.get("started_at")
        time_spent = None
        if started_at:
            try:
                time_spent = int(datetime.now(timezone.utc).timestamp() - float(started_at))
            except ValueError:
                time_spent = None

        score = 0
        answers_to_save = []

        for question in mission.questions:
            user_answer_raw = request.form.getlist(f'question_{question.id}')
            user_answer = set(map(int, user_answer_raw))

            if question.correct_answer:
                correct_answer = set(map(int, question.correct_answer.split(",")))
            else:
                correct_answer = set()

            is_correct = bool(user_answer) and user_answer == correct_answer
            if user_answer:
                if is_correct:
                    score += 1

            answers_to_save.append((question.id, ",".join(user_answer_raw), is_correct))

        total = len(mission.questions)

        # Словник для порівняння відповідей у result.html — доступний завжди, навіть для гостей
        answer_lookup = {}
        for question_id, answer_text, is_correct in answers_to_save:
            answer_lookup[question_id] = {
                "answered": bool(answer_text),
                "is_correct": is_correct
            }

        progress = None
        user = None

        if user_id:
            user = Users.query.get(user_id)

            # Перевіряємо, чи вже була пройдена місія
            existing_completed = UserMissionProgress.query.filter_by(
                user_id=user_id,
                mission_id=mission.id,
                completed=True
            ).first()

            was_already_completed = existing_completed is not None
            previous_tries = UserMissionProgress.query.filter_by(
                user_id=user_id,
                mission_id=mission.id
            ).count()

            # Оновлення streak
            today = datetime.now(timezone.utc).date()
            last_mission = UserMissionProgress.query.filter_by(
                user_id=user_id
            ).order_by(UserMissionProgress.completed_at.desc()).first()

            if last_mission and last_mission.completed_at:
                last_date = last_mission.completed_at.date()
                if last_date == today:
                    pass  # вже сьогодні проходив
                elif (today - last_date).days == 1:
                    user.streak += 1  # продовжуємо стрік
                else:
                    user.streak = 1   # обнуляємо, бо була перерва
            else:
                user.streak = 1  # перше проходження

            progress = UserMissionProgress(
                user_id=user_id,
                mission_id=mission.id,
                completed=(score == total),
                score_correct_answers=score,
                total_questions=total,
                xp_earned=mission.xp if score == total else 0,
                tries_number=previous_tries + 1,
                time_spent=time_spent,
                completed_at=datetime.now(timezone.utc) if score == total else None
            )
            db.session.add(progress)
            db.session.flush()

            for question_id, answer_text, is_correct in answers_to_save:
                db.session.add(UserAnswer(
                    user_progress_id=progress.id,
                    question_id=question_id,
                    user_answer=answer_text,
                    is_correct=is_correct
                ))

            db.session.flush()
            
            # Оновлюємо accuracy
            all_progress = UserMissionProgress.query.filter_by(user_id=user_id).all()
            total_correct = sum(p.score_correct_answers for p in all_progress)
            total_all_questions = sum(p.total_questions for p in all_progress)
            user.accuracy = round(total_correct / total_all_questions * 100, 1) if total_all_questions > 0 else 0.0

            # Додаємо XP та missions_completed тільки якщо місія пройдена і не була пройдена раніше
            if score == total and not was_already_completed:
                user.total_xp += mission.xp
                user.missions_completed += 1

            db.session.commit()

            user = Users.query.get(session["user_id"])

        return render_template("result.html", mission=mission, score=score, total=total, progress=progress, user=user, answer_lookup=answer_lookup)
    next_try_number = 1
    if user_id:
        previous_tries = UserMissionProgress.query.filter_by(
            user_id=user_id,
            mission_id=mission.id
        ).count()
        next_try_number = previous_tries + 1

    return render_template('mission.html', mission=mission, next_try_number=next_try_number, current_timestamp=datetime.now(timezone.utc).timestamp())




@app.route("/admin", methods=["GET", "POST"])
def admin():
    user_id = session.get("user_id")

    if user_id is None:
        return redirect("/login")

    user = Users.query.get(user_id)

    if not user or not user.admin:
        return "Forbidden", 403

    # --- ОТРИМУЄМО ДАНІ ---
    missions = Missions.query.all()

    # --- СТАТИСТИКА ---
    users_count = Users.query.count()
    missions_count = Missions.query.count()
    attempts_count = UserMissionProgress.query.count()
    user_count_verified = Users.query.filter_by(email_verified=True).count()
    total_xp = db.session.query(db.func.sum(Users.total_xp)).scalar() or 0

    # Активні користувачі (останні 30 днів)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    active_users = Users.query.filter(
        Users.last_login >= thirty_days_ago
    ).count()

    # Обробка пошуку
    search_email = request.args.get('search_email', '').strip()
    users = Users.query.all()

    if search_email:
        searched_user = Users.query.filter_by(email=search_email).first()
        users = [searched_user] if searched_user else []

    return render_template(
        'admin.html',
        users=users,
        missions=missions,
        search_email=search_email,
        users_count=users_count,
        user_count_verified=user_count_verified,
        missions_count=missions_count,
        attempts_count=attempts_count,
        total_xp=total_xp,
        active_users=active_users
    )




def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_to_cloudinary(file, folder="mediamission_content", resource_type="auto"):
    """Завантажує файл на Cloudinary з обробкою помилок"""
    try:
        if file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext in ['mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv']:
                resource_type = "video"
            elif ext in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg']:
                resource_type = "image"
            else:
                resource_type = "auto"

        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type=resource_type,
            use_filename=True,
            unique_filename=True,
            overwrite=False
        )

        return {
            'success': True,
            'url': result['secure_url'],
            'public_id': result['public_id'],
            'resource_type': result['resource_type']
        }

    except Exception as e:
        print(f"Помилка завантаження на Cloudinary: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def get_cloudinary_public_id(url):
    """
    Витягує (public_id, resource_type) з Cloudinary secure_url,
    щоб потім можна було видалити файл через cloudinary.uploader.destroy.
    Приклад URL: https://res.cloudinary.com/<cloud>/image/upload/v123456/folder/name.jpg
    """
    if not url or "res.cloudinary.com" not in url:
        return None, None

    resource_type = "video" if "/video/upload/" in url else "image"
    match = re.search(r"/upload/(?:v\d+/)?(.+?)\.\w+$", url)
    if not match:
        return None, None

    return match.group(1), resource_type


def delete_from_cloudinary(url):
    """Видаляє файл з Cloudinary за його URL, якщо це дійсно Cloudinary-файл"""
    public_id, resource_type = get_cloudinary_public_id(url)
    if not public_id:
        return

    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
    except Exception as e:
        print(f"Не вдалося видалити файл з Cloudinary ({public_id}): {e}")


def create_notification_for_mission(mission, admin_id):
    notif = Notification(
        title="notification_new_mission_title",  # ключ перекладу, не готовий текст
        body="notification_new_mission_body",     # ключ перекладу
        mission_id=mission.id,
        created_by=admin_id
    )
    db.session.add(notif)
    db.session.flush()  # щоб отримати notif.id

    user_ids = [u.id for u in Users.query.with_entities(Users.id).all()]
    if user_ids:
        db.session.bulk_insert_mappings(NotificationRecipient, [
            {"notification_id": notif.id, "user_id": uid} for uid in user_ids
        ])




@app.route("/api/admin/add_mission", methods=["POST"])
def add_mission():
    user_id = session.get("user_id")
    if user_id is None:
        return {"error": "Unauthorized"}, 401

    user = Users.query.get(user_id)
    if not user or not user.admin:
        return {"error": "Forbidden"}, 403

    try:
        title = request.form.get("title", "").strip()
        subtitle = request.form.get("subtitle", "").strip()
        exercise = request.form.get("exercise", "").strip()
        mission_type = request.form.get("type", "news")
        difficulty = request.form.get("difficulty", "1")
        xp = request.form.get("xp", "20")
        time_val = request.form.get("time", "5")

        if not title or not subtitle:
            return {"error": "Назва та підзаголовок обов'язкові"}, 400

        contents = json.loads(request.form.get("contents", "[]"))
        questions = json.loads(request.form.get("questions", "[]"))

        if not questions:
            return {"error": "Додайте хоча б одне питання"}, 400

        # Обкладинка місії — завжди йде на Cloudinary
        image_filename = None
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                upload_result = upload_to_cloudinary(file, folder="mediamission_covers")
                if upload_result['success']:
                    image_filename = upload_result['url']
                else:
                    print(f"Помилка завантаження обкладинки: {upload_result.get('error')}")

        mission = Missions(
            title=title,
            subtitle=subtitle,
            description="",
            exercise=exercise,
            type=mission_type,
            difficulty=difficulty,
            xp=xp,
            time=time_val,
            image=image_filename
        )
        db.session.add(mission)
        db.session.flush()  # Отримуємо mission.id без коміту

        # Контент місії (текст/фото/відео) — фото й відео теж на Cloudinary
        for paragraph in contents:
            text_value = paragraph.get("text", "")
            order = paragraph.get("order", 0)

            file_key = f"content_file_{order}"

            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename:
                    is_video = text_value.startswith("[VIDEO]")

                    upload_result = upload_to_cloudinary(
                        file,
                        folder="mediamission_content",
                        resource_type="video" if is_video else "image"
                    )

                    if upload_result['success']:
                        rest = text_value.split("\n", 1)
                        caption = rest[1] if len(rest) > 1 else ""
                        marker = "[VIDEO]" if is_video else "[IMAGE]"
                        text_value = f"{marker}{upload_result['url']}" + (f"\n{caption}" if caption else "")
                    else:
                        print(f"Помилка завантаження файлу для абзацу {order}: {upload_result.get('error')}")
                        continue

            db.session.add(MissionContent(
                mission_id=mission.id,
                paragraph_order=order,
                text=text_value
            ))

        # Питання
        for q in questions:
            if not q.get("correct_answer"):
                return {"error": f"Питання '{q.get('question', '')}' не має правильних відповідей"}, 400

            question = Questions(
                mission_id=mission.id,
                type=q.get("type", "single_choice"),
                question=q.get("question", ""),
                correct_answer=",".join(map(str, q.get("correct_answer", [])))
            )
            db.session.add(question)
            db.session.flush()

            for i, option in enumerate(q.get("options", [])):
                if option.strip():
                    db.session.add(Options(
                        question_id=question.id,
                        option_order=i,
                        option_text=option.strip()
                    ))

        create_notification_for_mission(mission, user_id)

        db.session.commit()
        return {"success": True, "message": "Місію успішно створено", "mission_id": mission.id}

    except Exception as e:
        db.session.rollback()
        print(f"Помилка створення місії: {e}")
        return {"error": str(e)}, 500




@app.route("/api/session_login", methods=["POST"])
def session_login():
    data = request.get_json()
    if not data or "uid" not in data:
        return {"success": False, "error": "нема uid"}, 400

    user = Users.query.filter_by(firebase_uid=data["uid"]).first()
    if user is None:
        return {"success": False, "error": "user не знайдено"}, 404

    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    session["firebase_uid"] = user.firebase_uid
    session["user_id"] = user.id
    return {"success": True}




@app.route("/register", methods=["GET", "POST"])
def register():
    return render_template('register.html')




@app.route("/api/create_user", methods=["POST"])
def create_user():
    data = request.get_json()
    if not data.get("email"):
        return {"success": False, "error": "email обов'язковий"}, 400

    user = Users.query.filter_by(firebase_uid=data["uid"]).first()

    if user:
        return {"success": True}

    new_user = Users(
        firebase_uid=data["uid"],
        display_name=data.get("display_name") or "Користувач",
        email=data.get("email", ""),
        provider=data.get("provider", "password"),
        total_xp=0,
        missions_completed=0,
        accuracy=0,
        streak=0,
        created_at=datetime.now(timezone.utc),
        email_verified=data.get("email_verified", False)
    )

    db.session.add(new_user)
    db.session.commit()
    return {"success": True}




@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    return render_template('login.html')




@app.route("/profile", methods=['GET', 'POST'])
def profile():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for('login'))

    user = db.session.get(Users, user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # Перевіряємо нові досягнення
    newly_unlocked = check_and_unlock_achievements(user_id)
    if newly_unlocked:
        # Можна додати flash повідомлення
        flash(f"🎉 Ви отримали нові досягнення!", 'success')
    
    # Отримуємо всі досягнення користувача
    # У роуті profile
    user_achievements = db.session.query(
        Achievement,
        UserAchievement.unlocked_at,
        UserAchievement.is_new
    ).outerjoin(
        UserAchievement,
        (Achievement.id == UserAchievement.achievement_id) & (UserAchievement.user_id == user_id)
    ).order_by(
        # Спочатку розблоковані, потім заблоковані
        UserAchievement.unlocked_at.desc().nullslast(),
        Achievement.category,
        Achievement.id
    ).all()
    
    # Форматуємо для шаблону
    achievements_data = []
    for achievement, unlocked_at, is_new in user_achievements:
        # Отримуємо переклад залежно від мови
        lang = g.lang
        title = getattr(achievement, f'title_{lang}', achievement.title_en)
        description = getattr(achievement, f'description_{lang}', achievement.description_en)
        
        achievements_data.append({
            'id': achievement.id,
            'key': achievement.key,
            'title': title,
            'description': description,
            'icon': achievement.icon,
            'category': achievement.category,
            'xp_reward': achievement.xp_reward,
            'unlocked': unlocked_at is not None,
            'unlocked_at': unlocked_at,
            'is_new': is_new if unlocked_at else False,
        })
    
    # ... інша статистика ...
    user_progress_time_spent = UserMissionProgress.query.filter_by(user_id=user_id).filter(
        UserMissionProgress.time_spent < 4000
    ).count()
    
    recent_progress = UserMissionProgress.query.filter_by(user_id=user_id).order_by(
        UserMissionProgress.completed_at.desc(),
        UserMissionProgress.id.desc()
    ).limit(5).all()
    
    total_attempts = UserMissionProgress.query.filter_by(user_id=user_id).count()
    successful_attempts = UserMissionProgress.query.filter_by(user_id=user_id, completed=True).count()
    success_rate = round(successful_attempts / total_attempts * 100) if total_attempts > 0 else 0
    
    return render_template(
        'profile.html',
        user=user,
        user_achievements=achievements_data,
        recent_progress=recent_progress,
        user_progress_time_spent=user_progress_time_spent,
        total_attempts=total_attempts,
        successful_attempts=successful_attempts,
        success_rate=success_rate,
        newly_unlocked=newly_unlocked
    )




@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return {"success": True}



@app.route("/api/check_provider", methods=["POST"])
def check_provider():
    data = request.get_json()
    try:
        user_record = firebase_auth.get_user_by_email(data["email"])
        providers = [p.provider_id for p in user_record.provider_data]
        return {"providers": providers}
    except firebase_auth.UserNotFoundError:
        return {"providers": []}




@app.route("/api/update_verification_status", methods=["POST"])
def update_verification_status():
    data = request.get_json()
    if not data or "uid" not in data:
        return {"success": False}, 400

    user = Users.query.filter_by(firebase_uid=data["uid"]).first()
    if user is None:
        return {"success": False, "error": "user not found"}, 404

    if data.get("email_verified") and not user.email_verified:
        user.email_verified = True
        db.session.commit()

    return {"success": True, "email_verified": user.email_verified}




@app.route("/upload-avatar", methods=["POST"])
def upload_avatar():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    file = request.files.get("avatar")
    if not file or not file.filename:
        return redirect("/profile")

    filename = secure_filename(file.filename)
    if not allowed_file(filename):
        return redirect("/profile")

    user = db.session.get(Users, user_id)

    # Видаляємо старий аватар з Cloudinary, якщо він там був
    if user.avatar:
        delete_from_cloudinary(user.avatar)

    result = cloudinary.uploader.upload(
        file,
        folder="mediamission_avatars",
        public_id=str(uuid.uuid4()),
        overwrite=True
    )

    user.avatar = result["secure_url"]
    db.session.commit()

    return redirect("/profile")


def get_avatar_color(name):
    if not name:
        return AVATAR_COLORS[0]
    index = sum(ord(char) for char in name) % len(AVATAR_COLORS)
    return AVATAR_COLORS[index]

@app.context_processor
def inject_avatar_color():
    return {"avatar_color": get_avatar_color}




@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return {"error": "Forbidden"}, 403

    users_count = Users.query.count()
    missions_count = Missions.query.count()
    attempts_count = UserMissionProgress.query.count()
    user_count_verified = Users.query.filter_by(email_verified=True).count()

    return {
        "success": True,
        "stats": {
            "users": users_count,
            "missions": missions_count,
            "attempts": attempts_count,
            "user_count_verified": user_count_verified
        }
    }


# ----------------------------------------------------
# ADMIN API ROUTE: Пошук користувача за Email
# ----------------------------------------------------
@app.route("/api/admin/find_user", methods=["POST"])
def find_user_by_email():
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return {"error": "Forbidden"}, 403

    data = request.get_json()
    email_query = data.get("email", "").strip()

    if not email_query:
        return {"success": False, "error": "Email не вказано"}, 400

    target_user = Users.query.filter_by(email=email_query).first()

    if not target_user:
        return {"success": False, "error": "Користувача з таким email не знайдено"}, 404

    return {
        "success": True,
        "user": {
            "id": target_user.id,
            "display_name": target_user.display_name,
            "email": target_user.email,
            "total_xp": target_user.total_xp,
            "admin": target_user.admin,
            "missions_completed": target_user.missions_completed,
            "accuracy": target_user.accuracy,
            "streak": target_user.streak,
            "created_at": target_user.created_at.strftime('%Y-%m-%d %H:%M') if target_user.created_at else "—",
            "last_login": target_user.last_login.strftime('%Y-%m-%d %H:%M') if target_user.last_login else "—"
        }
    }

# ----------------------------------------------------
# ADMIN API ROUTE: Видалення користувача
# ----------------------------------------------------
@app.route("/api/admin/delete_user/<int:target_id>", methods=["DELETE"])
def delete_user(target_id):
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return {"error": "Forbidden"}, 403

    target_user = Users.query.get(target_id)
    if not target_user:
        return {"success": False, "error": "Користувача не знайдено"}, 404

    if target_user.id == current_user.id:
        return {"success": False, "error": "Ви не можете видалити самого себе!"}, 400

    if target_user.avatar:
        delete_from_cloudinary(target_user.avatar)

    UserMissionProgress.query.filter_by(user_id=target_user.id).delete()

    db.session.delete(target_user)
    db.session.commit()

    return {"success": True}


@app.route("/leaderboard", methods=["GET", "POST"])
def leaderboard():

    top_by_xp = (
        Users.query
        .filter_by(allowed_to_show=True)
        .order_by(Users.total_xp.desc())
        .limit(50)
        .all()
    )

    top_by_missions = (
        Users.query
        .filter_by(allowed_to_show=True)
        .filter(Users.missions_completed > 0)
        .order_by(Users.missions_completed.desc())
        .limit(50)
        .all()
    )

    top_by_accuracy = (
        Users.query
        .filter_by(allowed_to_show=True)
        .filter(Users.missions_completed >= 5)
        .order_by(Users.accuracy.desc())
        .limit(50)
        .all()
    )

    current_user_id = session.get("user_id")

    def get_rank(sorted_list, user_id):
        for index, u in enumerate(sorted_list, start=1):
            if u.id == user_id:
                return index
        return None

    return render_template(
        "leaderboard.html",
        top_by_xp=top_by_xp,
        top_by_missions=top_by_missions,
        top_by_accuracy=top_by_accuracy,
        current_user_id=current_user_id,
        rank_xp=get_rank(top_by_xp, current_user_id) if current_user_id else None,
        rank_missions=get_rank(top_by_missions, current_user_id) if current_user_id else None,
        rank_accuracy=get_rank(top_by_accuracy, current_user_id) if current_user_id else None,
    )



@app.route('/api/admin/missions', methods=['GET'])
def get_admin_missions_list():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return jsonify({"error": "Forbidden"}), 403

    missions = Missions.query.order_by(Missions.id.desc()).all()

    result = []
    for m in missions:
        result.append({
            'id': m.id,
            'title': m.title,
            'subtitle': getattr(m, 'subtitle', ''),
            'type': getattr(m, 'type', None) or 'Інше',
            'difficulty': str(getattr(m, 'difficulty', '1')),
            'xp': getattr(m, 'xp', 0),
            'time': getattr(m, 'time', 0),
            'has_notifications': Notification.query.filter_by(mission_id=m.id).count() > 0,
            'notifications_count': Notification.query.filter_by(mission_id=m.id).count()
        })

    return jsonify({'success': True, 'missions': result})




@app.route("/api/admin/mission_dependencies/<int:mission_id>", methods=["GET"])
def get_mission_dependencies(mission_id):
    """Перевіряє залежності місії перед видаленням"""
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return {"error": "Forbidden"}, 403

    try:
        notifications = Notification.query.filter_by(mission_id=mission_id).all()
        notification_ids = [n.id for n in notifications]

        recipient_count = 0
        if notification_ids:
            recipient_count = NotificationRecipient.query.filter(
                NotificationRecipient.notification_id.in_(notification_ids)
            ).count()

        questions = Questions.query.filter_by(mission_id=mission_id).all()
        question_ids = [q.id for q in questions]

        answers_count = 0
        if question_ids:
            answers_count = UserAnswer.query.filter(
                UserAnswer.question_id.in_(question_ids)
            ).count()

        progress_count = UserMissionProgress.query.filter_by(mission_id=mission_id).count()

        return jsonify({
            'success': True,
            'dependencies': {
                'notifications': len(notifications),
                'notification_recipients': recipient_count,
                'questions': len(questions),
                'user_answers': answers_count,
                'user_progress': progress_count
            },
            'has_dependencies': any([
                len(notifications) > 0,
                recipient_count > 0,
                len(questions) > 0,
                answers_count > 0,
                progress_count > 0
            ])
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route("/api/admin/delete_mission/<int:mission_id>", methods=["DELETE"])
def delete_mission(mission_id):
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return {"error": "Forbidden"}, 403

    mission = Missions.query.get(mission_id)
    if not mission:
        return {"success": False, "error": "Місію не знайдено"}, 404

    try:
        # 1. Видаляємо обкладинку місії з Cloudinary
        if mission.image:
            delete_from_cloudinary(mission.image)

        # 2. Видаляємо фото/відео з тексту контенту місії з Cloudinary
        for content in mission.contents:
            if content.text.startswith("[IMAGE]") or content.text.startswith("[VIDEO]"):
                first_line = content.text.split("\n", 1)[0]
                media_url = first_line[7:]  # прибираємо маркер [IMAGE]/[VIDEO]
                delete_from_cloudinary(media_url)

        # 3. Видаляємо сповіщення, пов'язані з місією
        notifications = Notification.query.filter_by(mission_id=mission_id).all()
        notification_ids = [n.id for n in notifications]

        if notification_ids:
            NotificationRecipient.query.filter(
                NotificationRecipient.notification_id.in_(notification_ids)
            ).delete(synchronize_session=False)

            Notification.query.filter_by(mission_id=mission_id).delete(synchronize_session=False)

        # 4. Знаходимо всі ID питань, які належать цій місії
        questions = Questions.query.filter_by(mission_id=mission_id).all()
        question_ids = [q.id for q in questions]

        if question_ids:
            # 5. Видаляємо відповіді користувачів
            UserAnswer.query.filter(UserAnswer.question_id.in_(question_ids)).delete(synchronize_session=False)

        # 6. Видаляємо прогрес користувачів
        UserMissionProgress.query.filter_by(mission_id=mission_id).delete(synchronize_session=False)

        # 7. Видаляємо саму місію (каскадом підуть MissionContent, Questions, Options)
        db.session.delete(mission)
        db.session.commit()

        return {"success": True, "message": f"Місію #{mission_id} успішно видалено разом з усіма залежностями"}

    except Exception as e:
        db.session.rollback()
        print(f"Помилка видалення місії: {e}")
        return {"success": False, "error": str(e)}, 500




@app.route("/admin/notifications", methods=["POST"])
@admin_required
def send_notification():
    admin_id = session.get("user_id")

    title = request.form["title"]
    body = request.form["body"]
    mission_id = request.form.get("mission_id") or None
    target = request.form.get("target")

    notif = Notification(title=title, body=body, mission_id=mission_id, created_by=admin_id)
    db.session.add(notif)
    db.session.flush()

    if target == "all":
        user_ids = [u.id for u in Users.query.with_entities(Users.id).all()]
    else:
        user_ids = request.form.getlist("user_ids")

    db.session.bulk_insert_mappings(NotificationRecipient, [
        {"notification_id": notif.id, "user_id": uid} for uid in user_ids
    ])
    db.session.commit()
    return redirect(url_for("admin"))



@app.route("/api/admin/delete_notification/<int:notification_id>", methods=["DELETE"])
def delete_notification(notification_id):
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return {"error": "Forbidden"}, 403

    try:
        NotificationRecipient.query.filter_by(notification_id=notification_id).delete(synchronize_session=False)

        notification = Notification.query.get(notification_id)
        if notification:
            db.session.delete(notification)
            db.session.commit()
            return {"success": True, "message": "Сповіщення видалено"}
        else:
            return {"success": False, "error": "Сповіщення не знайдено"}, 404

    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}, 500




@app.context_processor
def inject_notifications():
    user_id = session.get("user_id")
    if not user_id:
        return {}

    unread_count = NotificationRecipient.query.filter_by(user_id=user_id, is_read=False).count()
    latest_notifications = (
        NotificationRecipient.query
        .filter_by(user_id=user_id)
        .join(Notification)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )
    return dict(unread_count=unread_count, latest_notifications=latest_notifications)



@app.route('/notifications')
def notifications():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for('login'))

    items = (
        NotificationRecipient.query
        .filter_by(user_id=user_id)
        .join(Notification)
        .order_by(Notification.created_at.desc())
        .all()
    )

    unread_ids = [n.id for n in items if not n.is_read]
    if unread_ids:
        NotificationRecipient.query.filter(NotificationRecipient.id.in_(unread_ids)).update(
            {"is_read": True, "read_at": datetime.utcnow()}, synchronize_session=False
        )
        db.session.commit()

    return render_template("notifications.html", items=items)




@app.route('/api/auth/custom_verify_email', methods=['POST'])
def custom_verify_email():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'error': 'Email обов\'язковий'}), 400

    try:
        verify_link = auth.generate_email_verification_link(email)
        html_body = render_template('emails/verify_email.html', verify_link=verify_link)

        msg = Message(
            subject="Verify your email | MediaMission",
            recipients=[email],
            html=html_body
        )
        mail.send(msg)

        return jsonify({'success': True, 'message': 'Лист верифікації надіслано!'})
    except Exception as e:
        print(f"Помилка відправки листа верифікації: {e}")
        return jsonify({'success': False, 'error': 'Не вдалося надіслати лист.'}), 500


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False') == 'TRUE')