# gamification.py
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Dict, Any

from extensions import db
from models import Achievement, UserAchievement, Users, UserMissionProgress, Missions


@dataclass
class League:
    name: str
    icon: str
    badge_class: str


class GamificationSystem:
    # --- 1. РОЗРАХУНОК XP ТА РІВНІВ ---

    @staticmethod
    def get_xp_for_level(level: int) -> int:
        if level <= 0:
            return 0

        thresholds = {1: 100, 2: 200, 3: 300, 4: 400, 5: 500,
                      6: 600, 7: 700, 8: 800, 9: 900, 10: 1000}

        if level in thresholds:
            return thresholds[level]

        return 1000 + (level - 10) * 150

    @classmethod
    def calculate_level_info(cls, total_xp: int) -> Dict[str, Any]:
        current_level = 0
        while total_xp >= cls.get_xp_for_level(current_level + 1):
            current_level += 1

        current_level_threshold = cls.get_xp_for_level(current_level)
        next_level_threshold = cls.get_xp_for_level(current_level + 1)

        xp_in_current_level = total_xp - current_level_threshold
        xp_required_for_next = next_level_threshold - current_level_threshold
        progress_percent = min(100, int((xp_in_current_level / xp_required_for_next) * 100))

        return {
            "level": current_level,
            "xp_in_current_level": xp_in_current_level,
            "xp_required_for_next": xp_required_for_next,
            "progress_percent": progress_percent
        }

    # --- 2. ЛІГИ ТА РАНГИ ---

    @staticmethod
    def get_league(level: int) -> League:
        if level >= 100:
            return League("Олімпійська ліга", "💎", "bg-danger text-light")
        if level >= 90:
            return League("Чемпіонська ліга", "👑", "bg-warning text-dark")
        if level >= 80:
            return League("Сапфірова ліга", "🟦", "bg-primary")
        if level >= 70:
            return League("Рубінова ліга", "🔻", "bg-danger")
        if level >= 60:
            return League("Смарагдова ліга", "🟢", "bg-success")
        if level >= 50:
            return League("Діамантова ліга", "💠", "bg-info text-dark")
        if level >= 40:
            return League("Золота ліга", "🟡", "bg-info")
        if level >= 30:
            return League("Срібна ліга", "⚪", "bg-warning text-dark")
        if level >= 18:
            return League("Бронзова ліга", "🟤", "bg-secondary")
        if level >= 10:
            return League("Залізна ліга", "⚙️", "bg-dark text-light")
        return League("Дерев'яна ліга", "🪵", "bg-light text-dark border")

    @staticmethod
    def calculate_rank(completed_missions: int, level: int, accuracy: float) -> str:
        if completed_missions >= 360 and level >= 100 and accuracy >= 80:
            return "Ультра ранг"
        if completed_missions >= 300 and level >= 80 and accuracy >= 80:
            return "Легендарний ранг"
        if completed_missions >= 175 and level >= 50 and accuracy >= 80:
            return "Мастер ранг"
        if completed_missions >= 60 and level >= 20 and accuracy >= 70:
            return "Золотий ранг"
        if completed_missions >= 25 and level >= 10 and accuracy >= 60:
            return "Срібний ранг"
        if completed_missions >= 10 and level >= 5 and accuracy >= 50:
            return "Бронзовий ранг"
        return "Новачок"


# --- 3. АЧІВКИ (окремі модульні функції, працюють з реальною БД-моделлю) ---

ACHIEVEMENTS_DATA = [
    {
        'key': 'first_steps',
        'title_uk': 'Перші кроки', 'title_de': 'Erste Schritte', 'title_en': 'First Steps',
        'description_uk': 'Зареєструватися та завершити 1-шу місію',
        'description_de': 'Registrieren und die 1. Mission abschließen',
        'description_en': 'Register and complete your 1st mission',
        'icon': 'bi-flag-fill', 'category': 'missions', 'xp_reward': 10
    },
    {
        'key': 'fake_detective',
        'title_uk': 'Детектив фейків', 'title_de': 'Fälschungsdetektiv', 'title_en': 'Fake Detective',
        'description_uk': 'Розпізнати 5 маніпуляцій у новинах',
        'description_de': '5 Manipulationen in Nachrichten erkennen',
        'description_en': 'Spot 5 manipulations in news',
        'icon': 'bi-search', 'category': 'missions', 'xp_reward': 20
    },
    {
        'key': 'unbreakable_logic',
        'title_uk': 'Непробивна логіка', 'title_de': 'Unerschütterliche Logik', 'title_en': 'Unbreakable Logic',
        'description_uk': 'Отримати 1000 XP на платформі',
        'description_de': '1000 XP auf der Plattform erhalten',
        'description_en': 'Earn 1000 XP on the platform',
        'icon': 'bi-shield-check', 'category': 'xp', 'xp_reward': 50
    },
    {
        'key': 'streak_master',
        'title_uk': '🔥 Майстер серії', 'title_de': '🔥 Serien-Meister', 'title_en': '🔥 Streak Master',
        'description_uk': 'Досягти 7-денної серії',
        'description_de': '7-Tage-Serie erreichen',
        'description_en': 'Reach 7-day streak',
        'icon': 'bi-fire', 'category': 'streak', 'xp_reward': 30
    },
    {
        'key': 'xp_hunter',
        'title_uk': '🎯 Мисливець за XP', 'title_de': '🎯 XP-Jäger', 'title_en': '🎯 XP Hunter',
        'description_uk': 'Накопичити 5000 XP',
        'description_de': '5000 XP sammeln',
        'description_en': 'Accumulate 5000 XP',
        'icon': 'bi-target', 'category': 'xp', 'xp_reward': 100
    },
    {
        'key': 'mission_master',
        'title_uk': '🏆 Майстер місій', 'title_de': '🏆 Missions-Meister', 'title_en': '🏆 Mission Master',
        'description_uk': 'Пройди 25 місій',
        'description_de': '25 Missionen abschließen',
        'description_en': 'Complete 25 missions',
        'icon': 'bi-trophy', 'category': 'missions', 'xp_reward': 75
    },
    {
        'key': 'accuracy_expert',
        'title_uk': '🎯 Експерт точності', 'title_de': '🎯 Genauigkeits-Experte', 'title_en': '🎯 Accuracy Expert',
        'description_uk': 'Досягти 90% точності відповідей',
        'description_de': '90% Antwortgenauigkeit erreichen',
        'description_en': 'Reach 90% answer accuracy',
        'icon': 'bi-bullseye', 'category': 'accuracy', 'xp_reward': 40
    },
    {
        'key': 'media_literate',
        'title_uk': '📰 Медіаграмотний', 'title_de': '📰 Medienkompetent', 'title_en': '📰 Media Literate',
        'description_uk': 'Пройди місії всіх типів',
        'description_de': 'Missionen aller Typen abschließen',
        'description_en': 'Complete missions of all types',
        'icon': 'bi-newspaper', 'category': 'missions', 'xp_reward': 60
    },
    {
        'key': 'speedrunner',
        'title_uk': '⚡ Спринтер', 'title_de': '⚡ Sprinter', 'title_en': '⚡ Speedrunner',
        'description_uk': 'Пройди місію менш ніж за 30 секунд',
        'description_de': 'Mission in weniger als 30 Sekunden abschließen',
        'description_en': 'Complete a mission in under 30 seconds',
        'icon': 'bi-lightning', 'category': 'speed', 'xp_reward': 25
    },
    {
        'key': 'perfect_score',
        'title_uk': '💯 Ідеальний рахунок', 'title_de': '💯 Perfekte Punktzahl', 'title_en': '💯 Perfect Score',
        'description_uk': 'Отримати 100% на будь-якій місії',
        'description_de': '100% bei jeder Mission erreichen',
        'description_en': 'Get 100% on any mission',
        'icon': 'bi-stars', 'category': 'accuracy', 'xp_reward': 35
    },
]

CATEGORY_LABELS = {
    'missions': {'uk': 'Місії', 'de': 'Missionen', 'en': 'Missions'},
    'xp': {'uk': 'Досвід', 'de': 'Erfahrung', 'en': 'Experience'},
    'streak': {'uk': 'Серія', 'de': 'Serie', 'en': 'Streak'},
    'accuracy': {'uk': 'Точність', 'de': 'Genauigkeit', 'en': 'Accuracy'},
    'speed': {'uk': 'Швидкість', 'de': 'Geschwindigkeit', 'en': 'Speed'},
}


def init_achievements():
    for data in ACHIEVEMENTS_DATA:
        existing = Achievement.query.filter_by(key=data['key']).first()
        if not existing:
            db.session.add(Achievement(**data))
    db.session.commit()


def _check_condition(key, user):
    if key == 'first_steps':
        return user.missions_completed >= 1
    if key == 'fake_detective':
        return user.missions_completed >= 5
    if key == 'unbreakable_logic':
        return user.total_xp >= 1000
    if key == 'streak_master':
        return user.streak >= 7
    if key == 'xp_hunter':
        return user.total_xp >= 5000
    if key == 'mission_master':
        return user.missions_completed >= 25
    if key == 'accuracy_expert':
        return user.accuracy >= 90
    if key == 'media_literate':
        completed_types = db.session.query(Missions.type).join(
            UserMissionProgress, UserMissionProgress.mission_id == Missions.id
        ).filter(
            UserMissionProgress.user_id == user.id,
            UserMissionProgress.completed == True
        ).distinct().all()
        all_types = db.session.query(Missions.type).distinct().all()
        return set(t[0] for t in completed_types) == set(t[0] for t in all_types) and len(all_types) > 0
    if key == 'speedrunner':
        return UserMissionProgress.query.filter(
            UserMissionProgress.user_id == user.id,
            UserMissionProgress.completed == True,
            UserMissionProgress.time_spent < 30
        ).first() is not None
    if key == 'perfect_score':
        return UserMissionProgress.query.filter(
            UserMissionProgress.user_id == user.id,
            UserMissionProgress.completed == True,
            UserMissionProgress.score_correct_answers == UserMissionProgress.total_questions
        ).first() is not None
    return False


def check_and_unlock_achievements(user_id):
    user = Users.query.get(user_id)
    if not user:
        return []

    unlocked_ids = set(
        ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user_id).all()
    )

    newly_unlocked = []
    for achievement in Achievement.query.all():
        if achievement.id in unlocked_ids:
            continue

        if _check_condition(achievement.key, user):
            db.session.add(UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                unlocked_at=datetime.now(timezone.utc),
                is_new=True
            ))
            newly_unlocked.append(achievement)
            if achievement.xp_reward > 0:
                user.total_xp += achievement.xp_reward

    if newly_unlocked:
        db.session.commit()

    return newly_unlocked