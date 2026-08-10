import os

UKRAINIAN_MONTHS = [
    "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"
]

AVATAR_COLORS = [
    "#FF6B6B", "#F06595", "#CC5DE8", "#845EF7", "#5C7CFA",
    "#339AF0", "#22B8CF", "#20C997", "#51CF66", "#94D82D",
    "#FCC419", "#FF922B", "#FF8787", "#748FFC", "#63E6BE",
]

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_avatar_color(name):
    if not name:
        return AVATAR_COLORS[0]
    index = sum(ord(char) for char in name) % len(AVATAR_COLORS)
    return AVATAR_COLORS[index]

def date_uk(value):
    if value is None:
        return ""
    return f"{value.strftime('%H:%M')}, {value.day} {UKRAINIAN_MONTHS[value.month - 1]}"