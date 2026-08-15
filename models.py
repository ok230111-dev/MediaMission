from datetime import datetime, timezone
from flask import session, redirect, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import JSON
from extensions import db

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

    contents = db.relationship(
        "MissionContent", 
        backref="mission", 
        lazy=True, 
        cascade="all, delete-orphan",
        order_by="MissionContent.paragraph_order"
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

    options = db.relationship(
        "Options", 
        backref="question", 
        lazy=True, 
        cascade="all, delete-orphan",
        order_by="Options.option_order"
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
    notification_token = db.Column(db.String(500), nullable=True)

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
    __tablename__ = "notification"
    
    id = db.Column(db.Integer, primary_key=True)
    title_json = db.Column(JSON, nullable=True)
    body_json = db.Column(JSON, nullable=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=True)
    mission = db.relationship("Missions")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = db.relationship("Users", foreign_keys=[created_by])
    comments = db.relationship("NotificationComment", backref="notification", cascade="all, delete-orphan", order_by="desc(NotificationComment.created_at)")
    reactions = db.relationship("NotificationReaction", backref="notification", cascade="all, delete-orphan")

class NotificationRecipient(db.Model):
    __tablename__ = "notification_recipients"
    
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("notification.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)

    notification = db.relationship("Notification") 
    user = db.relationship("Users")

class NotificationComment(db.Model):
    __tablename__ = 'notification_comments'

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("notification.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("Users")

class NotificationReaction(db.Model):
    __tablename__ = 'notification_reactions'

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("notification.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)
    user = db.relationship("Users")

    __table_args__ = (
        db.UniqueConstraint('notification_id', 'user_id', 'reaction_type', name='unique_user_reaction'),
    )

class Achievement(db.Model):
    __tablename__ = "achievements"
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    title_uk = db.Column(db.String(200), nullable=False)
    title_de = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200), nullable=False)
    description_uk = db.Column(db.String(500), nullable=False)
    description_de = db.Column(db.String(500), nullable=False)
    description_en = db.Column(db.String(500), nullable=False)
    icon = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), default='general')
    xp_reward = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    user_achievements = db.relationship("UserAchievement", backref="achievement", lazy=True, cascade="all, delete-orphan")

class UserAchievement(db.Model):
    __tablename__ = "user_achievements"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey("achievements.id"), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_new = db.Column(db.Boolean, default=True)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='unique_user_achievement'),)
    
    user = db.relationship("Users", backref=db.backref("user_achievements", lazy=True, cascade="all, delete-orphan"))

class SupportTicket(db.Model):
    __tablename__ = "support_tickets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category = db.Column(db.String(50), nullable=False)
    category_label = db.Column(db.String(100), nullable=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=True)
    issue_type = db.Column(db.String(100), nullable=True)
    issue_type_label = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=True)
    screenshot_url = db.Column(db.String(500), nullable=True)
    browser_info = db.Column(JSON, nullable=True)
    status = db.Column(db.String(20), default="open")
    admin_reply = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("Users")
    mission = db.relationship("Missions")

class Idea(db.Model):
    __tablename__ = "ideas"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    page = db.Column(db.String(50), nullable=False)
    page_label = db.Column(db.String(150), nullable=True)
    category = db.Column(db.String(50), nullable=False)
    category_label = db.Column(db.String(100), nullable=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    attachment_url = db.Column(db.String(500), nullable=True)
    admin_reply = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    status = db.Column(db.String(20), default="new")

    user = db.relationship("Users")


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_a_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user_b_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    last_message_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user_a = db.relationship("Users", foreign_keys=[user_a_id])
    user_b = db.relationship("Users", foreign_keys=[user_b_id])
    messages = db.relationship(
        "ChatMessage",
        backref="conversation",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )

    __table_args__ = (
        db.UniqueConstraint('user_a_id', 'user_b_id', name='unique_conversation_pair'),
    )


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sender = db.relationship("Users")
class IdeaAdminView(SecureModelView):
    column_list = ['id', 'title', 'category_label', 'page_label', 'status', 'created_at']
    column_searchable_list = ['title', 'description']
    column_filters = ['status', 'category', 'page']


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    display_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    text = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)  # адмін вмикає показ на головній
    is_featured = db.Column(db.Boolean, default=False)  # опційно: "вибрані" відгуки
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("Users")


class DailyTaskTemplate(db.Model):
    __tablename__ = "daily_task_templates"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)  # напр. "complete_1_mission"
    title_uk = db.Column(db.String(200), nullable=False)
    title_de = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200), nullable=False)
    icon = db.Column(db.String(10), default="🎯")
    task_type = db.Column(db.String(30), nullable=False)
    # можливі значення: "complete_mission", "perfect_mission", "earn_xp",
    # "mission_type", "send_message", "visit_leaderboard"
    target_value = db.Column(db.Integer, default=1)  # скільки треба зробити (1 місія, 50 XP тощо)
    extra_param = db.Column(db.String(50), nullable=True)  # напр. тип місії "news"/"video"
    xp_reward = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)


class UserDailyTask(db.Model):
    __tablename__ = "user_daily_tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("daily_task_templates.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)  # на який день це завдання
    progress = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    xp_claimed = db.Column(db.Boolean, default=False)

    template = db.relationship("DailyTaskTemplate")

    __table_args__ = (
        db.UniqueConstraint('user_id', 'template_id', 'date', name='unique_user_task_per_day'),
    )