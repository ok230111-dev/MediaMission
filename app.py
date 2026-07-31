from flask import Flask, render_template, request, redirect, url_for, session, g
from translations import translate
import requests
import smtplib
from flask_migrate import Migrate
import os
import uuid
import json
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from dotenv import load_dotenv
from datetime import datetime, timezone
import time
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
import cloudinary
import cloudinary.uploader



app = Flask(__name__)

load_dotenv()


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

UPLOAD_FOLDER = "static/uploads/avatars"

os.makedirs(os.path.join("static", "image"), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32).hex()) # Потрібно для Flask-Admin

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
admin.add_view(UserAdminView(Users, db.session))

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
            correct_answer = set(map(int, question.correct_answer.split(",")))

            is_correct = bool(user_answer) and user_answer == correct_answer
            if user_answer:
                if is_correct:
                    score += 1

            answers_to_save.append((question.id, ",".join(user_answer_raw), is_correct))

        total = len(mission.questions)

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

            # --- ВИПРАВЛЕННЯ: Оновлення streak ---
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

        return render_template("result.html", mission=mission, score=score, total=total, progress=progress)

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
    users = Users.query.all()
    missions = Missions.query.all()
    user_id = session.get("user_id")

    if user_id is None:
        return redirect("/login")

    user = Users.query.get(user_id)

    if not user.admin:
        return "Forbidden", 403

    # Обробка пошуку за email
    search_email = request.args.get('search_email', '').strip()
    searched_user = None

    users_count = Users.query.count()
    missions_count = Missions.query.count()
    attempts_count = UserMissionProgress.query.count()
    user_count_verified = Users.query.filter_by(email_verified=True).count()
    total_xp = db.session.query(db.func.sum(Users.total_xp)).scalar() or 0
    
    if search_email:
        searched_user = Users.query.filter_by(email=search_email).first()
        if searched_user:
            # Якщо знайдено, показуємо тільки цього користувача
            users = [searched_user]
        else:
            users = []  # Якщо не знайдено, показуємо порожній список
    
    return render_template('admin.html', users=users, missions=missions, searched_user=searched_user, search_email=search_email, users_count=users_count, user_count_verified=user_count_verified, missions_count=missions_count, attempts_count=attempts_count, total_xp=total_xp)




def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/api/admin/add_mission", methods=["POST"])
def add_mission():

    user_id = session.get("user_id")

    if user_id is None:
        return {"error": "Unauthorized"}, 401

    user = Users.query.get(user_id)

    if not user or not user.admin:
        return {"error": "Forbidden"}, 403

    # Тепер дані НЕ JSON, а form-data
    title = request.form["title"]
    subtitle = request.form["subtitle"]
    exercise = request.form["exercise"]
    mission_type = request.form["type"]
    difficulty = request.form["difficulty"]
    xp = request.form["xp"]
    time_val = request.form["time"]

    contents = json.loads(request.form["contents"])
    questions = json.loads(request.form["questions"])

    # Обробка файлу зображення
    image_filename = None
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit(".", 1)[1].lower()
            image_filename = f"{uuid.uuid4().hex}.{ext}"  # унікальне ім'я, щоб не було конфліктів
            file.save(os.path.join("static", "image", image_filename))

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
    db.session.commit()

    for paragraph in contents:
        db.session.add(MissionContent(
            mission_id=mission.id,
            paragraph_order=paragraph["order"],
            text=paragraph["text"]
        ))

    for q in questions:
        question = Questions(
            mission_id=mission.id,
            type=q["type"],
            question=q["question"],
            correct_answer=",".join(map(str, q["correct_answer"]))
        )
        db.session.add(question)
        db.session.flush()

        for i, option in enumerate(q["options"]):
            db.session.add(Options(
                question_id=question.id,
                option_order=i,
                option_text=option
            ))

    db.session.commit()
    return {"success": True}





@app.route("/api/session_login", methods=["POST"])
def session_login():
    data = request.get_json()
    if not data or "uid" not in data:
        return {"success": False, "error": "нема uid"}, 400

    user = Users.query.filter_by(firebase_uid=data["uid"]).first()
    if user is None:
        return {"success": False, "error": "user не знайдено"}, 404

    user.last_login = datetime.now(timezone.utc)   # ← оновлення тут, де і логічно
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
        email=data.get("email", ""),  #треба подивитися, тому що email потрібен і без нього таке собі
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
    return {"success":True}





@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    return render_template('login.html')




@app.route("/profile", methods=['GET', 'POST'])
def profile():
    missions = Missions.query.all()

    user_id = session.get("user_id")
    # Якщо в сесії ще немає progress, створюємо початковий
    if user_id is None:
        return redirect(url_for('login'))

    user = db.session.get(Users, user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    user_progress_time_spent =  (
        UserMissionProgress.query
        .filter_by(user_id=user_id)
        .filter(UserMissionProgress.time_spent < 4000)
        .count()
    )

    recent_progress = (
        UserMissionProgress.query
        .filter_by(user_id=user_id)
        .order_by(
            UserMissionProgress.completed_at.desc(),
            UserMissionProgress.id.desc()
        )
        .limit(5)
        .all()
    )

    total_attempts = UserMissionProgress.query.filter_by(user_id=user_id).count()

    return render_template(
        'profile.html',
        user=user,
        recent_progress=recent_progress,
        user_progress_time_spent=user_progress_time_spent,
        total_attempts=total_attempts
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

    result = cloudinary.uploader.upload(
        file,
        folder="mediamission_avatars",
        public_id=str(uuid.uuid4()),
        overwrite=True
    )

    user = db.session.get(Users, user_id)
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

    # Повертаємо детальну інформацію про користувача
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

    # Видаляємо всі зв'язані записи користувача
    UserMissionProgress.query.filter_by(user_id=target_user.id).delete()
    
    db.session.delete(target_user)
    db.session.commit()

    return {"success": True}


# ----------------------------------------------------
# ADMIN API ROUTE: Отримання списку місій та їх видалення
# ----------------------------------------------------
@app.route("/api/admin/missions", methods=["GET"])
def get_admin_missions():
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401
    
    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return {"error": "Forbidden"}, 403

    missions = Missions.query.all()
    result = [{
        "id": m.id,
        "title": m.title,
        "xp": m.xp,
        "difficulty": m.difficulty
    } for m in missions]

    return {"success": True, "missions": result}


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

    db.session.delete(mission)
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
    current_user_rank = None

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




# with app.app_context():
#     db.create_all()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False') == 'TRUE')