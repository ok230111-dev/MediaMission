import re
import random
import threading
from flask import Flask, Response, current_app, render_template, request, redirect, url_for, session, g, abort, jsonify, flash, send_from_directory
from flask_mail import Message
from sqlalchemy import JSON
import os
import uuid
import json
from auth import login_required
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from firebase_admin import auth
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta, date
import cloudinary
import cloudinary.uploader
from functools import wraps
from firebase_admin import messaging
import google.generativeai as genai
from groq import Groq
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from extensions import db, migrate, mail, admin
from models import (
    Missions, MissionContent, Questions, Options, Users, 
    UserMissionProgress, UserAnswer, Notification, NotificationRecipient,
    NotificationComment, NotificationReaction, Achievement, UserAchievement,
    SupportTicket, Idea, SecureAdminIndexView, UserAdminView, IdeaAdminView, Conversation, ChatMessage, Review, DailyTaskTemplate, UserDailyTask
)
from translations import translate
from utils import date_uk
from gamification import init_achievements, check_and_unlock_achievements

load_dotenv()

app = Flask(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "avif"}
MAX_IDEA_FILE_SIZE = 5 * 1024 * 1024

# Firebase initialization
cred_path = os.environ.get("FIREBASE_CRED_PATH", "serviceAccountKey.json")
if not os.path.exists(cred_path):
    alternatives = [
        "mediamission-a0b70-firebase-adminsdk-fbsvc-9cea1cad13.json",
        "serviceAccountKey.json.json",
        "mediamission-a0b70-firebase-adminsdk-fbsvc-a1ebbce726.json"
    ]
    for alt in alternatives:
        if os.path.exists(alt):
            cred_path = alt
            break
    else:
        print(f"❌ Файл облікових даних не знайдено!")
        print(f"Шукали: {cred_path}")
        raise FileNotFoundError("Не знайдено файл облікових даних Firebase")

print(f"✅ Використовуємо файл: {cred_path}")

cred = credentials.Certificate(cred_path)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

print("Firebase initialized!")

# App configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///mediamission.db").replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32).hex())

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('MediaMission', os.getenv('MAIL_USERNAME'))
app.config['MAIL_TIMEOUT'] = 15

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = os.environ.get("BREVO_API_KEY")
app.config['BREVO_API_KEY'] = os.environ.get("BREVO_API_KEY")

# Initialize extensions with app
db.init_app(app)
migrate.init_app(app, db)
mail.init_app(app)
admin.init_app(app)

# Cloudinary config
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# AI configs
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

AI_SYSTEM_PROMPT = """Ти — mmsAI, офіційний AI-Помічник освітнього сайту MediaMission для розвитку медіаграмотності та інформаційної грамотності серед українських дітей і підлітків у Німеччині (проєкт підтриманий грантом DAAD Zukunft Ukraine).

Твої задачі:
1. Представлятися як mmsAI та пояснювати поняття медіаграмотності й інформаційної грамотності простою мовою, з прикладами.
2. Допомагати розуміти, чому відповідь у місії правильна чи неправильна — пояснюй логіку, а не просто кажи "правильно/неправильно".
3. Відповідати на типові питання про сайт: як отримати XP, як працюють ліги/рейтинг, як змінити мову, як відновити пароль, як зв'язатися з підтримкою тощо.
4. Якщо не можеш допомогти або питання виходить за межі теми сайту — чесно скажи це і порадь звернутися в службу підтримки (сторінка /support).

Правила:
- Твоє ім'я — mmsAI. Називай себе так, якщо користувач запитує "Хто ти?".
- Відповідай мовою, якою до тебе звертаються.
- Будь доброзичливим і зрозумілим для підлітків — без зайвого канцеляриту.
- Тримай відповіді короткими (2-3 речень), якщо не просять детальніше.
- Ніколи не видавай прямі відповіді на питання тесту місії — замість цього поясни логіку і принцип.
- Не обговорюй теми, не пов'язані з сайтом, інфограмотністю чи медіаграмотністю."""

GROQ_CANDIDATE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

# Register admin views
admin.add_view(UserAdminView(Users, db.session))
admin.add_view(IdeaAdminView(Idea, db.session))

# ========== HELPER FUNCTIONS ==========

def asset_version(filename):
    filepath = os.path.join(app.static_folder, filename)
    try:
        mtime = int(os.path.getmtime(filepath))
        return mtime
    except OSError:
        return 0

app.jinja_env.globals['asset_version'] = asset_version

def send_email_via_api(subject, recipients, html_body):
    """Відправка email через Brevo HTTP API"""
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.environ.get("BREVO_API_KEY")

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": r} for r in recipients],
        sender={"name": "MediaMission", "email": os.environ.get("MAIL_USERNAME")},
        subject=subject,
        html_content=html_body
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        return True
    except ApiException as e:
        print(f"❌ Помилка відправки через Brevo API: {e}")
        return False

def upload_to_cloudinary(file, folder="mediamission_content", resource_type="auto"):
    """Завантажує файл на Cloudinary з обробкою помилок"""
    try:
        if file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext in ['mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv']:
                resource_type = "video"
            elif ext in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg']:
                resource_type = "image"

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
    if not url or "res.cloudinary.com" not in url:
        return None, None

    resource_type = "video" if "/video/upload/" in url else "image"
    match = re.search(r"/upload/(?:v\d+/)?(.+?)\.\w+$", url)
    if not match:
        return None, None

    return match.group(1), resource_type

def delete_from_cloudinary(url):
    public_id, resource_type = get_cloudinary_public_id(url)
    if not public_id:
        return

    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
    except Exception as e:
        print(f"Не вдалося видалити файл з Cloudinary ({public_id}): {e}")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_idea_file(filename):
    return allowed_file(filename)

AVATAR_COLORS = [
    "#FF6B6B", "#F06595", "#CC5DE8", "#845EF7", "#5C7CFA",
    "#339AF0", "#22B8CF", "#20C997", "#51CF66", "#94D82D",
    "#FCC419", "#FF922B", "#FF8787", "#748FFC", "#63E6BE",
]

def get_avatar_color(name):
    if not name:
        return AVATAR_COLORS[0]
    index = sum(ord(char) for char in name) % len(AVATAR_COLORS)
    return AVATAR_COLORS[index]

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

def create_notification_for_mission(mission, admin_id):
    notif = Notification(
        title_json={
            "uk": translate("notification_new_mission_title", "uk"),
            "de": translate("notification_new_mission_title", "de"),
            "en": translate("notification_new_mission_title", "en"),
        },
        body_json={
            "uk": translate("notification_new_mission_body", "uk"),
            "de": translate("notification_new_mission_body", "de"),
            "en": translate("notification_new_mission_body", "en"),
        },
        mission_id=mission.id,
        created_by=admin_id
    )
    db.session.add(notif)
    db.session.flush()

    user_ids = [u.id for u in Users.query.with_entities(Users.id).all()]
    if user_ids:
        db.session.bulk_insert_mappings(NotificationRecipient, [
            {"notification_id": notif.id, "user_id": uid} for uid in user_ids
        ])

def notify_admins_new_ticket(ticket):
    reporter_email = ticket.user.email if ticket.user else "Гість"
    category_label = ticket.category
    summary = f"{category_label} — {ticket.issue_type or ''}".strip(" —")

    admins = Users.query.filter_by(admin=True).all()
    if admins:
        notif = Notification(
            title_json={
                "uk": "Нове звернення в підтримку",
                "de": "Neue Support-Anfrage",
                "en": "New support ticket"
            },
            body_json={
                "uk": f"#{ticket.id}: {summary} (від {reporter_email})",
                "de": f"#{ticket.id}: {summary} (von {reporter_email})",
                "en": f"#{ticket.id}: {summary} (from {reporter_email})"
            },
            created_by=ticket.user_id
        )
        db.session.add(notif)
        db.session.flush()

        admin_ids = [a.id for a in admins]
        db.session.bulk_insert_mappings(NotificationRecipient, [
            {"notification_id": notif.id, "user_id": aid} for aid in admin_ids
        ])
        db.session.commit()

    support_email = os.environ.get("MAIL_USERNAME")
    if support_email:
        try:
            html_content = render_template(
                "emails/new_support_ticket.html",
                ticket=ticket,
                reporter_email=reporter_email
            )
            send_email_via_api(
                subject=f"[MediaMission Support] Нове звернення #{ticket.id}",
                recipients=[support_email],
                html_body=html_content
            )
        except Exception as e:
            print(f"Не вдалося підготувати email про звернення #{ticket.id}: {e}")

def notify_admins_new_idea(idea):
    admins = Users.query.filter_by(admin=True).all()
    if not admins:
        return

    notification = Notification(
        title_json={
            "uk": f"Нова ідея: {idea.title}",
            "en": f"New idea: {idea.title}",
            "de": f"Neue Idee: {idea.title}",
        },
        body_json={
            "uk": f"{idea.user.display_name} запропонував(ла) ідею для «{idea.page_label or idea.page}» ({idea.category_label or idea.category})",
            "en": f"{idea.user.display_name} suggested an idea for \"{idea.page_label or idea.page}\" ({idea.category_label or idea.category})",
            "de": f"{idea.user.display_name} hat eine Idee für „{idea.page_label or idea.page}“ vorgeschlagen ({idea.category_label or idea.category})",
        },
        mission_id=None,
        created_by=idea.user_id,
    )
    db.session.add(notification)
    db.session.flush()

    recipients = [
        NotificationRecipient(notification_id=notification.id, user_id=admin.id)
        for admin in admins
    ]
    db.session.bulk_save_objects(recipients)
    db.session.commit()

    support_email = os.environ.get("MAIL_USERNAME")
    if support_email:
        try:
            html_content = f"""
                <h3>Нова ідея #{idea.id}</h3>
                <p><strong>Від:</strong> {idea.user.display_name} ({idea.user.email})</p>
                <p><strong>Сторінка:</strong> {idea.page_label or idea.page}</p>
                <p><strong>Категорія:</strong> {idea.category_label or idea.category}</p>
                <p><strong>Заголовок:</strong> {idea.title}</p>
                <p><strong>Опис:</strong> {idea.description}</p>
            """

            send_email_via_api(
                subject=f"[MediaMission] Нова ідея #{idea.id}",
                recipients=[support_email],
                html_body=html_content
            )
        except Exception as e:
            print(f"Не вдалося підготувати email про ідею #{idea.id}: {e}")

def send_push_notification_to_tokens(title, body, tokens, url="/"):
    if not tokens:
        return

    for start in range(0, len(tokens), 500):
        batch_tokens = tokens[start:start + 500]
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    icon="/static/images/logo.png"
                ),
                fcm_options=messaging.WebpushFCMOptions(
                    link=url
                )
            ),
            tokens=batch_tokens
        )
        try:
            response = messaging.send_each_for_multicast(message)
            print(f"✅ Push-повідомлення надіслано: успішно {response.success_count}/{len(batch_tokens)}")
            
            if response.failure_count > 0:
                for index, resp in enumerate(response.responses):
                    if not resp.success:
                        print(f"❌ Помилка для токена {batch_tokens[index]}: {resp.exception}")
        except Exception as e:
            print(f"❌ Помилка при відправці push-повідомлень: {e}")

# ========== CONTEXT PROCESSORS ==========

@app.before_request
def set_language():
    lang = None
    g.user = None

    user_id = session.get("user_id")
    if user_id:
        user = Users.query.get(user_id)
        if user:
            g.user = user
            lang = user.language

    if lang is None:
        lang = session.get("language", "uk")

    g.lang = lang

@app.context_processor
def inject_translate():
    return {"t": lambda key: translate(key, g.lang)}

@app.context_processor
def inject_current_year():
    return {"current_year": datetime.now(timezone.utc).year}

@app.context_processor
def inject_avatar_color():
    return {"avatar_color": get_avatar_color}

@app.context_processor
def inject_notifications():
    user_id = session.get("user_id")
    user = None
    if user_id:
        user = Users.query.get(user_id)
    
    if not user_id or not user:
        return {"unread_count": 0, "latest_notifications": []}

    try:
        unread_count = NotificationRecipient.query.filter_by(user_id=user_id, is_read=False).count()
        
        latest_notifications = (
            NotificationRecipient.query
            .filter_by(user_id=user_id)
            .join(Notification)
            .order_by(Notification.created_at.desc())
            .limit(5)
            .all()
        )
    except Exception as e:
        print(f"❌ Помилка в context processor: {e}")
        return {"unread_count": 0, "latest_notifications": []}
    
    return {
        "unread_count": unread_count,
        "latest_notifications": latest_notifications,
        "current_user": user
    }

@app.template_filter('date_uk')
def date_uk_filter(value):
    if value is None:
        return ""
    return f"{value.strftime('%H:%M')}, {value.day} {['січня','лютого','березня','квітня','травня','червня','липня','серпня','вересня','жовтня','листопада','грудня'][value.month - 1]}"

# ========== ROUTES ==========

@app.route("/robots.txt")
def robots():
    return Response(
        f"""User-agent: *
Allow: /

Disallow: /profile
Disallow: /notifications
Disallow: /api/
Disallow: /admin

Sitemap: {request.url_root}sitemap.xml
""",
        mimetype="text/plain"
    )

@app.route("/sitemap.xml")
def sitemap():
    pages = []
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

@app.route("/")
def index():
    users_count = Users.query.count()
    missions_count = Missions.query.count()
    total_xp = db.session.query(db.func.sum(Users.total_xp)).scalar() or 0

    featured_reviews = (
            Review.query
            .filter_by(is_approved=True)
            .order_by(Review.created_at.desc())
            .limit(6)
            .all()
        )
    
    return render_template('index.html', users_count=users_count, missions_count=missions_count, total_xp=total_xp, featured_reviews=featured_reviews)


@app.route("/reviews", methods=["GET", "POST"])
def reviews():
    user_id = session.get("user_id")
    user = Users.query.get(user_id) if user_id else None

    if request.method == "POST":
        rating = request.form.get("rating", "").strip()
        text = request.form.get("text", "").strip()
        display_name = request.form.get("display_name", "").strip()

        if not text or not rating:
            flash(translate("reviews_fill_all_fields", g.lang), "danger")
            return redirect(url_for("reviews"))

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash(translate("reviews_invalid_rating", g.lang), "danger")
            return redirect(url_for("reviews"))

        if not display_name:
            display_name = user.display_name if user else "Anonymous"

        if len(text) > 1000:
            flash(translate("reviews_too_long", g.lang), "danger")
            return redirect(url_for("reviews"))

        review = Review(
            user_id=user.id if user else None,
            display_name=display_name,
            rating=rating,
            text=text,
            is_approved=False
        )
        db.session.add(review)
        db.session.commit()

        flash(translate("reviews_success_flash", g.lang), "success")
        return redirect(url_for("reviews"))

    return render_template("reviews.html", response_title=translate("reviews_title", g.lang), user=user)

@app.route("/daily-tasks")
def daily_tasks():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    tasks = get_or_assign_daily_tasks(user_id)
    return render_template("daily_tasks.html", tasks=tasks)

@app.route("/missions-overview")
def missions_overview():
    missions = Missions.query.all()
    return render_template('missions.html', missions=missions)

def get_or_assign_daily_tasks(user_id):
    today = date.today()

    existing_tasks = UserDailyTask.query.filter_by(user_id=user_id, date=today).all()
    if existing_tasks:
        return existing_tasks

    all_templates = DailyTaskTemplate.query.filter_by(is_active=True).all()
    if len(all_templates) <= 3:
        chosen = all_templates
    else:
        chosen = random.sample(all_templates, 3)

    new_tasks = []
    for template in chosen:
        task = UserDailyTask(user_id=user_id, template_id=template.id, date=today, progress=0)
        db.session.add(task)
        new_tasks.append(task)

    db.session.commit()
    return new_tasks

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

            today = datetime.now(timezone.utc).date()
            last_mission = UserMissionProgress.query.filter_by(
                user_id=user_id
            ).order_by(UserMissionProgress.completed_at.desc()).first()

            if last_mission and last_mission.completed_at:
                last_date = last_mission.completed_at.date()
                if last_date == today:
                    pass
                elif (today - last_date).days == 1:
                    user.streak += 1
                else:
                    user.streak = 1
            else:
                user.streak = 1

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
            
            all_progress = UserMissionProgress.query.filter_by(user_id=user_id).all()
            total_correct = sum(p.score_correct_answers for p in all_progress)
            total_all_questions = sum(p.total_questions for p in all_progress)
            user.accuracy = round(total_correct / total_all_questions * 100, 1) if total_all_questions > 0 else 0.0

            def update_daily_tasks_on_mission(user_id, mission, score, total, xp_earned):
                today = date.today()
                tasks = UserDailyTask.query.filter_by(user_id=user_id, date=today, is_completed=False).all()

                for task in tasks:
                    template = task.template

                    if template.task_type == "complete_mission":
                        task.progress += 1
                    elif template.task_type == "perfect_mission" and score == total:
                        task.progress += 1
                    elif template.task_type == "earn_xp":
                        task.progress += xp_earned
                    elif template.task_type == "mission_type" and mission.type == template.extra_param:
                        task.progress += 1

                    if task.progress >= template.target_value and not task.is_completed:
                        task.is_completed = True
                        task.completed_at = datetime.now(timezone.utc)

                db.session.commit()

            if score == total and not was_already_completed:
                user.total_xp += mission.xp
                user.missions_completed += 1

            db.session.commit()
            user = Users.query.get(session["user_id"])

            if user_id:
                update_daily_tasks_on_mission(user_id, mission, score, total, mission.xp if score == total else 0)

        return render_template("result.html", mission=mission, score=score, total=total, progress=progress, user=user, answer_lookup=answer_lookup)
    
    next_try_number = 1
    if user_id:
        previous_tries = UserMissionProgress.query.filter_by(
            user_id=user_id,
            mission_id=mission.id
        ).count()
        next_try_number = previous_tries + 1

    return render_template('mission.html', mission=mission, next_try_number=next_try_number, current_timestamp=datetime.now(timezone.utc).timestamp())

@app.route("/login", methods=["GET", "POST"])
def login():
    return render_template('login.html')

@app.route("/register", methods=["GET", "POST"])
def register():
    return render_template('register.html')

@app.route("/faq", methods=["GET", "POST"])
def faq():
    return render_template('faq.html')


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return {"success": True}

@app.route("/profile", methods=['GET', 'POST'])
def profile():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for('login'))

    user = db.session.get(Users, user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    newly_unlocked = check_and_unlock_achievements(user_id)
    if newly_unlocked:
        flash(f"🎉 Ви отримали нові досягнення!", 'success')
    
    user_achievements = db.session.query(
        Achievement,
        UserAchievement.unlocked_at,
        UserAchievement.is_new
    ).outerjoin(
        UserAchievement,
        (Achievement.id == UserAchievement.achievement_id) & (UserAchievement.user_id == user_id)
    ).order_by(
        UserAchievement.unlocked_at.desc().nullslast(),
        Achievement.category,
        Achievement.id
    ).all()
    
    achievements_data = []
    for achievement, unlocked_at, is_new in user_achievements:
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
    
    recent_progress = UserMissionProgress.query.filter_by(user_id=user_id).order_by(
        UserMissionProgress.completed_at.desc(),
        UserMissionProgress.id.desc()
    ).limit(5).all()
    
    total_attempts = UserMissionProgress.query.filter_by(user_id=user_id).count()
    successful_attempts = UserMissionProgress.query.filter_by(user_id=user_id, completed=True).count()
    success_rate = round(successful_attempts / total_attempts * 100) if total_attempts > 0 else 0

    tasks = get_or_assign_daily_tasks(user_id)
    
    return render_template(
        'profile.html',
        user=user,
        user_achievements=achievements_data,
        recent_progress=recent_progress,
        total_attempts=total_attempts,
        successful_attempts=successful_attempts,
        success_rate=success_rate,
        newly_unlocked=newly_unlocked,
        tasks=tasks
    )

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

@app.route("/support")
def support():
    missions = Missions.query.order_by(Missions.title).all()
    return render_template("support.html", missions=missions)

@app.route("/support-idea")
def support_idea():
    missions = Missions.query.order_by(Missions.title).all()
    return render_template("support-idea.html", missions=missions)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/offline")
def offline():
    return render_template("offline.html")

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')

@app.route('/firebase-messaging-sw.js')
def firebase_messaging_sw():
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')

# ========== API ROUTES ==========

@app.route("/api/daily_tasks/claim/<int:task_id>", methods=["POST"])
def claim_daily_task(task_id):
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    task = UserDailyTask.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return {"error": "Завдання не знайдено"}, 404

    if not task.is_completed:
        return {"error": "Завдання ще не виконано"}, 400

    if task.xp_claimed:
        return {"error": "Нагороду вже отримано"}, 400

    user = db.session.get(Users, user_id)
    user.total_xp += task.template.xp_reward
    task.xp_claimed = True

    db.session.commit()

    return {"success": True, "xp_earned": task.template.xp_reward}

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

    next_page = request.referrer or url_for('index')
    return redirect(next_page)

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

@app.route("/api/session_login", methods=["POST"])
def session_login():
    data = request.get_json()
    if not data or "uid" not in data:
        return {"success": False, "error": "нема uid"}, 400

    user = Users.query.filter_by(firebase_uid=data["uid"]).first()
    if user is None:
        try:
            firebase_user = firebase_auth.get_user(data["uid"])
            provider = "password"
            if firebase_user.provider_data:
                provider = firebase_user.provider_data[0].provider_id or provider

            user = Users(
                firebase_uid=firebase_user.uid,
                display_name=firebase_user.display_name or "Користувач",
                email=firebase_user.email or "",
                provider=provider,
                email_verified=firebase_user.email_verified,
                total_xp=0,
                missions_completed=0,
                accuracy=0,
                streak=0,
                created_at=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc)
            )
            db.session.add(user)
            db.session.commit()
        except firebase_auth.UserNotFoundError:
            return {"success": False, "error": "user не знайдено"}, 404
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}, 500

    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    session["firebase_uid"] = user.firebase_uid
    session["user_id"] = user.id
    return {"success": True}

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

@app.route("/api/save_notification_token", methods=["POST"])
@login_required
def save_notification_token():
    data = request.get_json()

    if not data or "token" not in data:
        return jsonify(success=False, error="token required"), 400

    user = g.user
    if not user:
        return jsonify(success=False, error="User session not found"), 401

    user.notification_token = data["token"]
    db.session.commit()

    return jsonify(success=True)


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
            {"is_read": True, "read_at": datetime.now(timezone.utc)}, synchronize_session=False
        )
        db.session.commit()

    conversations = Conversation.query.filter(
        db.or_(
            Conversation.user_a_id == user_id,
            Conversation.user_b_id == user_id
        )
    ).order_by(Conversation.last_message_at.desc()).all()

    conv_data = []
    for conv in conversations:
        other_user = conv.user_b if conv.user_a_id == user_id else conv.user_a
        last_message = conv.messages[-1] if conv.messages else None
        unread_count = ChatMessage.query.filter_by(
            conversation_id=conv.id, is_read=False
        ).filter(ChatMessage.sender_id != user_id).count()

        conv_data.append({
            "conversation": conv,
            "other_user": other_user,
            "last_message": last_message,
            "unread_count": unread_count
        })

    return render_template("notifications.html", items=items, conversations=conv_data)


# Старий /messages просто редіректить на нову об'єднану сторінку
@app.route('/messages')
def messages_list():
    return redirect(url_for('notifications'))


@app.route("/api/users/search", methods=["GET"])
def search_users():
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return {"users": []}

    results = Users.query.filter(
        db.or_(
            Users.display_name.ilike(f"%{query}%"),
            Users.email.ilike(f"%{query}%")
        ),
        Users.id != user_id,
        Users.allowed_to_show == True
    ).limit(10).all()

    return {
        "users": [
            {
                "id": u.id,
                "display_name": u.display_name,
                "email": u.email,
                "avatar": u.avatar
            } for u in results
        ]
    }


def get_or_create_conversation(user1_id, user2_id):
    a, b = sorted([user1_id, user2_id])

    conv = Conversation.query.filter_by(user_a_id=a, user_b_id=b).first()
    if conv is None:
        conv = Conversation(user_a_id=a, user_b_id=b)
        db.session.add(conv)
        db.session.commit()

    return conv


@app.route("/api/conversations/start", methods=["POST"])
def start_conversation():
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    data = request.get_json()
    other_user_id = data.get("user_id")

    other_user = db.session.get(Users, other_user_id)
    if not other_user:
        return {"error": "Користувача не знайдено"}, 404

    conv = get_or_create_conversation(user_id, other_user_id)
    return {"success": True, "conversation_id": conv.id}


@app.route("/messages/<int:conversation_id>", methods=["GET", "POST"])
def conversation_detail(conversation_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    conv = db.session.get(Conversation, conversation_id)
    if not conv or user_id not in (conv.user_a_id, conv.user_b_id):
        return "Forbidden", 403

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if text:
            msg = ChatMessage(conversation_id=conv.id, sender_id=user_id, text=text)
            db.session.add(msg)
            conv.last_message_at = datetime.now(timezone.utc)
            db.session.commit()
        return redirect(url_for("conversation_detail", conversation_id=conv.id))

    ChatMessage.query.filter_by(conversation_id=conv.id, is_read=False).filter(
        ChatMessage.sender_id != user_id
    ).update({"is_read": True}, synchronize_session=False)
    db.session.commit()

    other_user = conv.user_b if conv.user_a_id == user_id else conv.user_a

    return render_template(
        "conversation.html",
        conversation=conv,
        other_user=other_user,
        current_user_id=user_id
    )


@app.context_processor
def inject_notifications():
    user_id = session.get("user_id")
    if not user_id:
        return {"unread_count": 0, "latest_notifications": [], "unread_messages_count": 0}

    unread_count = NotificationRecipient.query.filter_by(user_id=user_id, is_read=False).count()

    latest_notifications = (
        NotificationRecipient.query
        .filter_by(user_id=user_id)
        .join(Notification)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    unread_messages_count = ChatMessage.query.join(Conversation).filter(
        db.or_(Conversation.user_a_id == user_id, Conversation.user_b_id == user_id),
        ChatMessage.sender_id != user_id,
        ChatMessage.is_read == False
    ).count()

    return {
        "unread_count": unread_count,
        "latest_notifications": latest_notifications,
        "unread_messages_count": unread_messages_count
    }


@app.route('/notifications/<int:notification_id>')
@login_required
def read_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    user = g.user
    if not user:
        return redirect(url_for('login'))

    recipient = NotificationRecipient.query.filter_by(
        notification_id=notification_id,
        user_id=user.id
    ).first()

    if recipient and not recipient.is_read:
        recipient.is_read = True
        recipient.read_at = datetime.utcnow()
        db.session.commit()

    lang = getattr(g, 'lang', 'uk')

    title = notification.title_json.get(lang) if notification.title_json else "Без заголовка"
    body = notification.body_json.get(lang) if notification.body_json else ""

    reactions_count = {
        'like': NotificationReaction.query.filter_by(notification_id=notification_id, reaction_type='like').count(),
        'heart': NotificationReaction.query.filter_by(notification_id=notification_id, reaction_type='heart').count(),
        'fire': NotificationReaction.query.filter_by(notification_id=notification_id, reaction_type='fire').count()
    }

    return render_template(
        'read_notification.html',
        notification=notification,
        title=title,
        body=body,
        reactions_count=reactions_count
    )

@app.route('/api/notifications/<int:notification_id>/react', methods=['POST'])
def add_reaction(notification_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() or {}
    reaction_type = data.get('reaction')

    if reaction_type not in ['like', 'heart', 'fire']:
        return jsonify({"success": False, "error": "Некоректний тип реакції"}), 400

    existing_reaction = NotificationReaction.query.filter_by(
        notification_id=notification_id,
        user_id=user.id,
        reaction_type=reaction_type
    ).first()

    if existing_reaction:
        db.session.delete(existing_reaction)
        action = 'removed'
    else:
        new_reaction = NotificationReaction(
            notification_id=notification_id,
            user_id=user.id,
            reaction_type=reaction_type
        )
        db.session.add(new_reaction)
        action = 'added'

    db.session.commit()

    new_count = NotificationReaction.query.filter_by(
        notification_id=notification_id,
        reaction_type=reaction_type
    ).count()

    return jsonify({"success": True, "action": action, "reaction": reaction_type, "new_count": new_count})

@app.route('/api/notifications/<int:notification_id>/comment', methods=['POST'])
def add_comment(notification_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() or {}
    text = data.get('text', '').strip()

    if not text:
        return jsonify({"success": False, "error": "Порожній коментар"}), 400

    comment = NotificationComment(
        notification_id=notification_id,
        user_id=user.id,
        text=text
    )
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        "success": True,
        "comment": {
            "id": comment.id,
            "author": user.display_name,
            "created_at": comment.created_at.strftime("%d.%m.%Y %H:%M"),
            "text": comment.text
        }
    })

@app.route("/api/notifications/mark_read", methods=["POST"])
def mark_notifications_read():
    user_id = session.get("user_id")
    if not user_id:
        return {"success": False}, 401

    NotificationRecipient.query.filter_by(user_id=user_id, is_read=False).update(
        {"is_read": True, "read_at": datetime.now(timezone.utc)},
        synchronize_session=False
    )
    db.session.commit()

    return {"success": True}

# ========== ADMIN ROUTES ==========

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect("/login")

    user = Users.query.get(user_id)
    if not user or not user.admin:
        return "Forbidden", 403

    missions = Missions.query.all()
    users_count = Users.query.count()
    missions_count = Missions.query.count()
    attempts_count = UserMissionProgress.query.count()
    user_count_verified = Users.query.filter_by(email_verified=True).count()
    total_xp = db.session.query(db.func.sum(Users.total_xp)).scalar() or 0

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    active_users = Users.query.filter(
        Users.last_login >= thirty_days_ago
    ).count()

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


@app.route("/api/admin/reviews", methods=["GET"])
def get_admin_reviews():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return jsonify({"error": "Forbidden"}), 403

    reviews = Review.query.order_by(Review.created_at.desc()).all()

    result = []
    for r in reviews:
        result.append({
            "id": r.id,
            "display_name": r.display_name,
            "rating": r.rating,
            "text": r.text,
            "is_approved": r.is_approved,
            "user_email": r.user.email if r.user else None,
            "created_at": r.created_at.strftime("%d.%m.%Y %H:%M")
        })

    return jsonify({"success": True, "reviews": result})


@app.route("/api/admin/reviews/<int:review_id>/approve", methods=["POST"])
def approve_review(review_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return jsonify({"error": "Forbidden"}), 403

    review = Review.query.get(review_id)
    if not review:
        return jsonify({"success": False, "error": "Відгук не знайдено"}), 404

    review.is_approved = True
    db.session.commit()

    return jsonify({"success": True})


@app.route("/api/admin/reviews/<int:review_id>/unapprove", methods=["POST"])
def unapprove_review(review_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return jsonify({"error": "Forbidden"}), 403

    review = Review.query.get(review_id)
    if not review:
        return jsonify({"success": False, "error": "Відгук не знайдено"}), 404

    review.is_approved = False
    db.session.commit()

    return jsonify({"success": True})


@app.route("/api/admin/reviews/<int:review_id>", methods=["DELETE"])
def delete_review(review_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return jsonify({"error": "Forbidden"}), 403

    review = Review.query.get(review_id)
    if not review:
        return jsonify({"success": False, "error": "Відгук не знайдено"}), 404

    db.session.delete(review)
    db.session.commit()

    return jsonify({"success": True})

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

    try:
        if target_user.avatar:
            delete_from_cloudinary(target_user.avatar)

        # Видаляємо сповіщення, ЯКІ ОТРИМАВ користувач
        NotificationRecipient.query.filter_by(user_id=target_user.id).delete()

        # НОВЕ: обнуляємо created_by у сповіщеннях, які СТВОРИВ цей користувач
        # (замість видалення самих сповіщень, щоб не втратити їх для інших отримувачів)
        Notification.query.filter_by(created_by=target_user.id).update(
            {"created_by": None}, synchronize_session=False
        )

        # НОВЕ: видаляємо коментарі та реакції користувача до сповіщень
        NotificationComment.query.filter_by(user_id=target_user.id).delete()
        NotificationReaction.query.filter_by(user_id=target_user.id).delete()

        # Видаляємо відповіді користувача (повʼязані через прогрес місій)
        progress_ids = [
            p.id for p in UserMissionProgress.query
            .filter_by(user_id=target_user.id)
            .with_entities(UserMissionProgress.id)
            .all()
        ]
        if progress_ids:
            UserAnswer.query.filter(
                UserAnswer.user_progress_id.in_(progress_ids)
            ).delete(synchronize_session=False)

        # Видаляємо прогрес місій
        UserMissionProgress.query.filter_by(user_id=target_user.id).delete()

        # НОВЕ: видаляємо звернення підтримки та ідеї користувача
        SupportTicket.query.filter_by(user_id=target_user.id).delete()
        Idea.query.filter_by(user_id=target_user.id).delete()

        # НОВЕ: видаляємо повідомлення чату та розмови користувача
        conversations = Conversation.query.filter(
            db.or_(Conversation.user_a_id == target_user.id, Conversation.user_b_id == target_user.id)
        ).all()
        conversation_ids = [c.id for c in conversations]
        if conversation_ids:
            ChatMessage.query.filter(ChatMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            Conversation.query.filter(Conversation.id.in_(conversation_ids)).delete(synchronize_session=False)

        db.session.delete(target_user)
        db.session.commit()

        return {"success": True}

    except Exception as e:
        db.session.rollback()
        print(f"Помилка видалення користувача: {e}")
        return {"success": False, "error": str(e)}, 500


# @app.route("/api/admin/delete_user/<int:target_id>", methods=["DELETE"])
# def delete_user(target_id):
#     user_id = session.get("user_id")
#     if not user_id:
#         return {"error": "Unauthorized"}, 401

#     current_user = Users.query.get(user_id)
#     if not current_user or not current_user.admin:
#         return {"error": "Forbidden"}, 403

#     target_user = Users.query.get(target_id)
#     if not target_user:
#         return {"success": False, "error": "Користувача не знайдено"}, 404

#     if target_user.id == current_user.id:
#         return {"success": False, "error": "Ви не можете видалити самого себе!"}, 400

#     try:
#         if target_user.avatar:
#             delete_from_cloudinary(target_user.avatar)

#         NotificationRecipient.query.filter_by(user_id=target_user.id).delete()

# # 1. Видаляємо прогрес місій (і пов'язані відповіді, якщо каскад не налаштований)
#         progress_ids = [p.id for p in UserMissionProgress.query.filter_by(user_id=target_user.id).all()]
#         if progress_ids:
#             UserAnswer.query.filter(UserAnswer.user_progress_id.in_(progress_ids)).delete(synchronize_session=False)
#         UserMissionProgress.query.filter_by(user_id=target_user.id).delete()

#         conversations = Conversation.query.filter(
#             db.or_(
#                 Conversation.user_a_id == target_user.id,
#                 Conversation.user_b_id == target_user.id
#             )
#         ).all()

#         # НОВЕ: обнуляємо created_by у сповіщеннях, які СТВОРИВ цей користувач
#         # (замість видалення самих сповіщень, щоб не втратити їх для інших отримувачів)
#         Notification.query.filter_by(created_by=target_user.id).update(
#             {"created_by": None}, synchronize_session=False
#         )

#         # НОВЕ: видаляємо коментарі та реакції користувача до сповіщень
#         NotificationComment.query.filter_by(user_id=target_user.id).delete()
#         NotificationReaction.query.filter_by(user_id=target_user.id).delete()

#         for conv in conversations:
#             ChatMessage.query.filter_by(conversation_id=conv.id).delete()
#             db.session.delete(conv)

#         db.session.delete(target_user)
#         db.session.commit()

#         return {"success": True}

#     except Exception as e:
#         db.session.rollback()
#         print(f"Помилка видалення користувача: {e}")
#         return {"success": False, "error": str(e)}, 500

@app.route("/api/admin/adjust_xp/<int:target_id>", methods=["POST"])
def adjust_user_xp(target_id):
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Unauthorized"}, 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return {"error": "Forbidden"}, 403

    target_user = Users.query.get(target_id)
    if not target_user:
        return {"success": False, "error": "Користувача не знайдено"}, 404

    data = request.get_json()
    try:
        amount = int(data.get("amount"))
    except (TypeError, ValueError):
        return {"success": False, "error": "Некоректне значення XP"}, 400

    if amount == 0:
        return {"success": False, "error": "Значення не може бути 0"}, 400

    target_user.total_xp = max(0, target_user.total_xp + amount)
    db.session.commit()

    return {
        "success": True,
        "new_total_xp": target_user.total_xp,
        "user_id": target_user.id
    }

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

        image_filename = None
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                upload_result = upload_to_cloudinary(file, folder="mediamission_covers")
                if upload_result['success']:
                    image_filename = upload_result['url']

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
        db.session.flush()

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
        if mission.image:
            delete_from_cloudinary(mission.image)

        for content in mission.contents:
            if content.text.startswith("[IMAGE]") or content.text.startswith("[VIDEO]"):
                first_line = content.text.split("\n", 1)[0]
                media_url = first_line[7:]
                delete_from_cloudinary(media_url)

        notifications = Notification.query.filter_by(mission_id=mission_id).all()
        notification_ids = [n.id for n in notifications]

        if notification_ids:
            NotificationRecipient.query.filter(
                NotificationRecipient.notification_id.in_(notification_ids)
            ).delete(synchronize_session=False)
            Notification.query.filter_by(mission_id=mission_id).delete(synchronize_session=False)

        questions = Questions.query.filter_by(mission_id=mission_id).all()
        question_ids = [q.id for q in questions]

        if question_ids:
            UserAnswer.query.filter(UserAnswer.question_id.in_(question_ids)).delete(synchronize_session=False)

        UserMissionProgress.query.filter_by(mission_id=mission_id).delete(synchronize_session=False)

        db.session.delete(mission)
        db.session.commit()

        return {"success": True, "message": f"Місію #{mission_id} успішно видалено"}

    except Exception as e:
        db.session.rollback()
        print(f"Помилка видалення місії: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route('/admin/notifications', methods=['POST'])
@admin_required
def send_admin_notification():
    title_uk = request.form.get('title_uk')
    body_uk = request.form.get('body_uk')
    
    title_de = request.form.get('title_de') or title_uk
    body_de = request.form.get('body_de') or body_uk
    
    title_en = request.form.get('title_en') or title_uk
    body_en = request.form.get('body_en') or body_uk

    title_json = {'uk': title_uk, 'de': title_de, 'en': title_en}
    body_json = {'uk': body_uk, 'de': body_de, 'en': body_en}

    new_notification = Notification(
        title_json=title_json,
        body_json=body_json,
        created_by=session.get("user_id")
    )
    db.session.add(new_notification)
    db.session.flush()  # отримуємо id, ще без коміту

    user_ids = [u.id for u in Users.query.with_entities(Users.id).all()]
    if user_ids:
        db.session.bulk_insert_mappings(NotificationRecipient, [
            {"notification_id": new_notification.id, "user_id": uid} for uid in user_ids
        ])

    db.session.commit()

    flash('Сповіщення успішно надіслано!', 'success')
    return redirect(url_for('admin_panel'))

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

@app.route("/api/admin/support_tickets", methods=["GET"])
def get_support_tickets():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return jsonify({"error": "Forbidden"}), 403

    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()

    result = []
    for tk in tickets:
        result.append({
            "id": tk.id,
            "category": tk.category_label or tk.category,
            "issue_type": tk.issue_type_label or tk.issue_type,
            "description": tk.description,
            "mission_title": tk.mission.title if tk.mission else None,
            "user_email": tk.user.email if tk.user else "Гість",
            "screenshot_url": tk.screenshot_url,
            "browser_info": tk.browser_info,
            "status": tk.status,
            "created_at": tk.created_at.strftime("%d.%m.%Y %H:%M")
        })

    return jsonify({"success": True, "tickets": result})

@app.route("/api/admin/support_tickets/<int:ticket_id>/status", methods=["POST"])
def update_ticket_status(ticket_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return jsonify({"error": "Forbidden"}), 403

    ticket = SupportTicket.query.get(ticket_id)
    if not ticket:
        return jsonify({"success": False, "error": "Звернення не знайдено"}), 404

    data = request.get_json()
    new_status = data.get("status")
    admin_reply = data.get("admin_reply")

    if new_status and new_status not in ("open", "answered", "solved", "closed"):
        return jsonify({"success": False, "error": "Некоректний статус"}), 400

    if new_status:
        ticket.status = new_status
    if admin_reply is not None:
        ticket.admin_reply = admin_reply

    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/admin/ideas", methods=["GET"])
def get_admin_ideas():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return jsonify({"error": "Forbidden"}), 403

    ideas = Idea.query.order_by(Idea.created_at.desc()).all()

    result = []
    for idea in ideas:
        result.append({
            "id": idea.id,
            "title": idea.title,
            "description": idea.description,
            "page": idea.page_label or idea.page,
            "category": idea.category_label or idea.category,
            "attachment_url": idea.attachment_url,
            "status": idea.status,
            "admin_reply": idea.admin_reply,
            "user_name": idea.user.display_name if idea.user else "—",
            "user_email": idea.user.email if idea.user else "—",
            "created_at": idea.created_at.strftime("%d.%m.%Y %H:%M"),
        })

    return jsonify({"success": True, "ideas": result})

@app.route("/api/admin/ideas/<int:idea_id>/status", methods=["POST"])
def update_idea_status(idea_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = Users.query.get(user_id)
    if not current_user or not current_user.admin:
        return jsonify({"error": "Forbidden"}), 403

    idea = Idea.query.get(idea_id)
    if not idea:
        return jsonify({"success": False, "error": "Ідею не знайдено"}), 404

    data = request.get_json()
    new_status = data.get("status")
    admin_reply = data.get("admin_reply")

    valid_statuses = ("new", "good", "must_have", "not_needed", "not_now")
    if new_status and new_status not in valid_statuses:
        return jsonify({"success": False, "error": "Некоректний статус"}), 400

    if new_status:
        idea.status = new_status
    if admin_reply is not None:
        idea.admin_reply = admin_reply

    db.session.commit()
    return jsonify({"success": True})

# ========== SUPPORT TICKET ROUTES ==========

@app.route("/api/support/submit_ticket", methods=["POST"])
def submit_support_ticket():
    user_id = session.get("user_id")

    category = request.form.get("category", "").strip()
    category_label = request.form.get("category_label", "").strip()
    mission_id = request.form.get("mission_id") or None
    issue_type = request.form.get("issue_type", "").strip()
    issue_type_label = request.form.get("issue_type_label", "").strip()
    description = request.form.get("description", "").strip()
    browser_info_raw = request.form.get("browser_info", "{}")

    if not category:
        return jsonify({"success": False, "error": "Оберіть категорію звернення"}), 400

    try:
        browser_info = json.loads(browser_info_raw)
    except (ValueError, TypeError):
        browser_info = {}

    screenshot_url = None
    if "screenshot" in request.files:
        file = request.files["screenshot"]
        if file and file.filename:
            upload_result = upload_to_cloudinary(file, folder="mediamission_support", resource_type="image")
            if upload_result["success"]:
                screenshot_url = upload_result["url"]

    ticket = SupportTicket(
        user_id=user_id,
        category=category,
        category_label=category_label or category,
        mission_id=int(mission_id) if mission_id else None,
        issue_type=issue_type,
        issue_type_label=issue_type_label or issue_type,
        description=description,
        screenshot_url=screenshot_url,
        browser_info=browser_info,
        status="open"
    )
    db.session.add(ticket)
    db.session.commit()

    notify_admins_new_ticket(ticket)

    return jsonify({"success": True, "ticket_id": ticket.id})

@app.route("/api/my_support_tickets", methods=["GET"])
def get_my_support_tickets():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    tickets = SupportTicket.query.filter_by(user_id=user_id).order_by(SupportTicket.created_at.desc()).all()

    result = []
    for tk in tickets:
        result.append({
            "id": tk.id,
            "category": tk.category_label or tk.category,
            "issue_type": tk.issue_type_label or tk.issue_type,
            "description": tk.description,
            "mission_title": tk.mission.title if tk.mission else None,
            "status": tk.status,
            "admin_reply": tk.admin_reply,
            "created_at": tk.created_at.strftime("%d.%m.%Y %H:%M")
        })

    return jsonify({"success": True, "tickets": result})

# ========== IDEA ROUTES ==========

IDEA_STATUSES = ("new", "good", "must_have", "not_needed", "not_now")

@app.route("/api/ideas", methods=["POST"])
def submit_idea():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    user = db.session.get(Users, user_id)
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    page = request.form.get("page", "").strip()
    page_label = request.form.get("page_label", "").strip()
    category = request.form.get("category", "").strip()
    category_label = request.form.get("category_label", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not page or not category or not title or not description:
        return jsonify({"error": "missing_fields"}), 400

    if len(title) > 100 or len(description) > 1000:
        return jsonify({"error": "too_long"}), 400

    attachment_url = None
    file = request.files.get("attachment")
    if file and file.filename:
        if not allowed_idea_file(file.filename):
            return jsonify({"error": "invalid_file_type"}), 400

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_IDEA_FILE_SIZE:
            return jsonify({"error": "file_too_large"}), 400

        upload_result = upload_to_cloudinary(file, folder="mediamission_ideas", resource_type="image")
        if upload_result["success"]:
            attachment_url = upload_result["url"]

    idea = Idea(
        user_id=user.id,
        page=page,
        page_label=page_label or None,
        category=category,
        category_label=category_label or None,
        title=title,
        description=description,
        attachment_url=attachment_url,
    )
    db.session.add(idea)
    db.session.commit()

    notify_admins_new_idea(idea)

    return jsonify({"success": True, "idea_id": idea.id}), 201

# ========== AUTH EMAIL ROUTES ==========

@app.route('/api/auth/custom_verify_email', methods=['POST'])
def custom_verify_email():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'error': 'Email обов\'язковий'}), 400

    try:
        verify_link = auth.generate_email_verification_link(email)
        html_body = render_template('emails/verify_email.html', verify_link=verify_link)

        sent = send_email_via_api(
            subject="Verify your email | MediaMission",
            recipients=[email],
            html_body=html_body
        )

        if not sent:
            return jsonify({'success': False, 'error': 'Не вдалося надіслати лист.'}), 500

        return jsonify({'success': True, 'message': 'Лист верифікації надіслано!'})
    except Exception as e:
        print(f"Помилка відправки листа верифікації: {e}")
        return jsonify({'success': False, 'error': 'Не вдалося надіслати лист.'}), 500

@app.route('/api/auth/custom_reset_password', methods=['POST'])
def custom_reset_password():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'error': 'Email обов\'язковий'}), 400

    user = Users.query.filter_by(email=email).first()
    lang = user.language if user and user.language else g.lang

    try:
        reset_link = auth.generate_password_reset_link(email)
        html_body = render_template('emails/reset_password.html', reset_link=reset_link, lang=lang)

        sent = send_email_via_api(
            subject=translate('reset_password_subject', lang),
            recipients=[email],
            html_body=html_body
        )

        if not sent:
            return jsonify({'success': False, 'error': 'Не вдалося надіслати лист.'}), 500

        return jsonify({'success': True, 'message': 'Лист для відновлення паролю надіслано!'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== AI ROUTE ==========

@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    now = datetime.now(timezone.utc)
    chat_log = session.get("ai_chat_log", [])
    chat_log = [t for t in chat_log if now - datetime.fromisoformat(t) < timedelta(minutes=5)]

    if len(chat_log) >= 15:
        return jsonify({"success": False, "error": "Забагато повідомлень. Зачекайте кілька хвилин."}), 429

    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    history = data.get("history", [])
    mission_context = data.get("mission_context")

    if not user_message:
        return jsonify({"success": False, "error": "Порожнє повідомлення"}), 400

    if len(user_message) > 2000:
        return jsonify({"success": False, "error": "Повідомлення занадто довге"}), 400

    system_prompt = AI_SYSTEM_PROMPT
    if mission_context:
        system_prompt += (
            f"\n\nКонтекст поточної місії:\n"
            f"Назва: {mission_context.get('title', '')}\n"
            f"Завдання: {mission_context.get('exercise', '')}"
        )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-10:]:
        role = "user" if msg.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_message})

    for model_name in GROQ_CANDIDATE_MODELS:
        try:
            raw_response = groq_client.chat.completions.with_raw_response.create(
                model=model_name,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            headers = raw_response.headers
            completion = raw_response.parse()
            reply_text = completion.choices[0].message.content

            chat_log.append(now.isoformat())
            session["ai_chat_log"] = chat_log

            rate_limit_info = {
                "remaining_requests": headers.get("x-ratelimit-remaining-requests"),
                "limit_requests": headers.get("x-ratelimit-limit-requests"),
                "remaining_tokens": headers.get("x-ratelimit-remaining-tokens"),
                "limit_tokens": headers.get("x-ratelimit-limit-tokens"),
            }

            return jsonify({
                "success": True,
                "reply": reply_text,
                "rate_limit": rate_limit_info
            })

        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str.lower() or "429" in error_str:
                print(f"⚠️ Ліміт вичерпано для {model_name}: {error_str}")
                continue
            elif "not found" in error_str.lower() or "404" in error_str:
                print(f"⚠️ Модель {model_name} не знайдена: {error_str}")
                continue
            else:
                print(f"❌ Помилка Groq API ({model_name}): {error_str}")
                continue

    return jsonify({
        "success": False,
        "error": "AI-помічник тимчасово перевантажений. Спробуйте через хвилину, або зверніться в підтримку."
    }), 429

# ========== DEBUG ROUTES ==========

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

        if avatar_value and not is_valid:
            user.avatar = None

    db.session.commit()
    return "<br>".join(output)



def init_daily_tasks():
    tasks = [
        {
            "key": "complete_1_mission",
            "title_uk": "Пройди 1 місію", "title_de": "Absolviere 1 Mission", "title_en": "Complete 1 mission",
            "icon": "🎯", "task_type": "complete_mission", "target_value": 1, "xp_reward": 10
        },
        {
            "key": "perfect_mission",
            "title_uk": "Пройди місію на 100%", "title_de": "Schließe eine Mission zu 100% ab", "title_en": "Complete a mission with 100%",
            "icon": "💯", "task_type": "perfect_mission", "target_value": 1, "xp_reward": 20
        },
        {
            "key": "earn_50_xp",
            "title_uk": "Заробіть 50 XP сьогодні", "title_de": "Verdiene heute 50 XP", "title_en": "Earn 50 XP today",
            "icon": "⚡", "task_type": "earn_xp", "target_value": 50, "xp_reward": 15
        },
        {
            "key": "mission_news",
            "title_uk": "Пройди місію-новину", "title_de": "Absolviere eine Nachrichten-Mission", "title_en": "Complete a news mission",
            "icon": "📰", "task_type": "mission_type", "target_value": 1, "extra_param": "news", "xp_reward": 10
        },
        {
            "key": "send_message",
            "title_uk": "Напиши повідомлення другу", "title_de": "Schreibe einem Freund eine Nachricht", "title_en": "Send a message to a friend",
            "icon": "💬", "task_type": "send_message", "target_value": 1, "xp_reward": 5
        },
    ]

    for data in tasks:
        existing = DailyTaskTemplate.query.filter_by(key=data["key"]).first()
        if not existing:
            db.session.add(DailyTaskTemplate(**data))

    db.session.commit()

# Виклик при старті додатка (БЕЗ db.create_all())
with app.app_context():
    try:
        init_daily_tasks()
    except Exception as e:
        db.session.rollback()
        print(f"Skipping init_daily_tasks: {e}")    
# ========== RUN APP ==========

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False') == 'TRUE')