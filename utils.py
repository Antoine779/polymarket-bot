from telegram import InlineKeyboardButton
from config import BOT_USERNAME


def get_share_button():
    return InlineKeyboardButton(
        "Compartilhar com amigos",
        url=f"https://t.me/share/url?url=t.me/{BOT_USERNAME}&text=Bot+gratuito+com+probabilidades+ao+vivo+da+Copa+do+Mundo+2026!"
    )