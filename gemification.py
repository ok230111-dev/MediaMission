# gamification.py

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class League:
    name: str
    icon: str
    badge_class: str


@dataclass
class Achievement:
    id: str
    title: str
    reward_title: str
    desc: str
    icon: str
    unlocked: bool


class GamificationSystem:
    # --- 1. РОЗРАХУНОК XP ТА РІВНІВ ---
    
    @staticmethod
    def get_xp_for_level(level: int) -> int:
        """Повертає загальну кількість XP, необхідну для досягнення вказаного рівня."""
        if level <= 0:
            return 0
        
        # Визначена сітка для перших 10 рівнів
        thresholds = {
            1: 80,
            2: 160,
            3: 250,
            4: 340,
            5: 440,
            6: 550,
            7: 660,
            8: 770,
            9: 880,
            10: 1000,
        }
        
        if level in thresholds:
            return thresholds[level]
        
        # З 10-го рівня і далі: +150 XP за кожен наступний рівень
        return 1000 + (level - 10) * 150

    @classmethod
    def calculate_level_info(cls, total_xp: int) -> Dict[str, Any]:
        """Обчислює поточний рівень, XP у межах рівня та прогрес у відсотках."""
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
        """Визначає лігу користувача залежно від рівня."""
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
            return League("Алмазна ліга", "🔷", "bg-info")
        if level >= 30:
            return League("Золота ліга", "🟡", "bg-warning text-dark")
        if level >= 18:  # 2500 XP відповідає 20-му рівню (2500 XP - межа для Срібної ліги)
            return League("Срібна ліга", "⚪", "bg-secondary")
        if level >= 10:
            return League("Бронзова ліга", "🟤", "bg-dark text-light")
            
        return League("Дерев'яна ліга", "🪵", "bg-light text-dark border")

    @staticmethod
    def calculate_rank(completed_missions: int, level: int, accuracy: float) -> str:
        """Обчислює ранг користувача на основі вимог до місій, рівня та точності."""
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

    # --- 3. АЧІВКИ ТА ЗВАННЯ ---

    @staticmethod
    def get_achievements(
        completed_missions: int,
        level: int,
        streak_days: int,
        all_types_completed: bool,
        video_watched: bool
    ) -> List[Achievement]:
        """Генерує список ачівок із прапорцем розблокування."""
        return [
            Achievement(
                id="first_mission",
                title="Перший крок",
                reward_title="Початківець",
                desc="Пройти першу місію",
                icon="🎯",
                unlocked=completed_missions >= 1
            ),
            Achievement(
                id="ten_missions",
                title="Старт покладено",
                reward_title="Десятник",
                desc="Пройти 10 місій",
                icon="⚔️",
                unlocked=completed_missions >= 10
            ),
            Achievement(
                id="streak_7",
                title="Незламна серія",
                reward_title="Незламний",
                desc="Тримати серію протягом 7 днів",
                icon="🔥",
                unlocked=streak_days >= 7
            ),
            Achievement(
                id="all_types",
                title="Універсал",
                reward_title="Експерт напрямків",
                desc="Пройти всі типи місій",
                icon="🧩",
                unlocked=all_types_completed
            ),
            Achievement(
                id="video_quest",
                title="Уважний глядач",
                reward_title="Медіаголік",
                desc="Переглянути навчальне відео або веб-матеріал",
                icon="🎬",
                unlocked=video_watched
            ),
            Achievement(
                id="level_50",
                title="Еліта платформи",
                reward_title="Майстер MediaMission",
                desc="Досягти 50-го рівня",
                icon="🛡️",
                unlocked=level >= 50
            ),
            Achievement(
                id="level_100",
                title="Абсолютна вершина",
                reward_title="Легенда MediaMission",
                desc="Досягти 100-го рівня",
                icon="👑",
                unlocked=level >= 100
            )
        ]

    # --- 4. ПОВНИЙ РОЗРАХУНОК ПРОФІЛЮ ---

    @classmethod
    def get_user_profile_data(cls, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Приймає словник з даними користувача і повертає повну структуровану статистику.
        """
        total_xp = user_data.get("total_xp", 0)
        completed_missions = user_data.get("completed_missions", 0)
        accuracy = user_data.get("accuracy", 0.0)
        streak_days = user_data.get("streak_days", 0)
        all_types_completed = user_data.get("all_types_completed", False)
        video_watched = user_data.get("video_watched", False)

        level_info = cls.calculate_level_info(total_xp)
        current_level = level_info["level"]

        league = cls.get_league(current_level)
        rank = cls.calculate_rank(completed_missions, current_level, accuracy)
        achievements = cls.get_achievements(
            completed_missions=completed_missions,
            level=current_level,
            streak_days=streak_days,
            all_types_completed=all_types_completed,
            video_watched=video_watched
        )

        return {
            "username": user_data.get("username", "Користувач"),
            "total_xp": total_xp,
            "level": current_level,
            "xp_in_current_level": level_info["xp_in_current_level"],
            "xp_required_for_next": level_info["xp_required_for_next"],
            "progress_percent": level_info["progress_percent"],
            "league": {
                "name": league.name,
                "icon": league.icon,
                "badge_class": league.badge_class
            },
            "rank": rank,
            "streak_days": streak_days,
            "completed_missions": completed_missions,
            "accuracy": accuracy,
            "achievements": [
                {
                    "id": a.id,
                    "title": a.title,
                    "reward_title": a.reward_title,
                    "desc": a.desc,
                    "icon": a.icon,
                    "unlocked": a.unlocked
                } for a in achievements
            ]
        }


# --- ТЕСТОВИЙ ЗАПУСК ---
if __name__ == "__main__":
    # Симуляція даних користувача з вашої бази даних
    sample_user = {
        "username": "Олександр",
        "total_xp": 1120,               # 10-й рівень (1000 XP) + 120 XP
        "completed_missions": 28,
        "accuracy": 65.0,
        "streak_days": 8,
        "all_types_completed": True,
        "video_watched": True
    }

    profile = GamificationSystem.get_user_profile_data(sample_user)

    print(f"=== Профіль користувача: {profile['username']} ===")
    print(f"Рівень: {profile['level']} ({profile['xp_in_current_level']}/{profile['xp_required_for_next']} XP, {profile['progress_percent']}%)")
    print(f"Ліга: {profile['league']['icon']} {profile['league']['name']}")
    print(f"Ранг: {profile['rank']}")
    print(f"Серія: {profile['streak_days']} днів 🔥")
    print("\nАчівки:")
    for ach in profile["achievements"]:
        status = f"✅ Звання: {ach['reward_title']}" if ach['unlocked'] else "🔒 Заблоковано"
        print(f" - {ach['icon']} {ach['title']}: {status}")