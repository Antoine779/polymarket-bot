import os
import json as j
import sqlite3
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue
import pytz

# 🔑 Token et lien affilié
TOKEN = os.environ.get("TOKEN")
AFFILIATE_LINK = "https://polymarket.com?via=yZWX33z"
BRASILIA_TZ = pytz.timezone("America/Sao_Paulo")

# 📦 Base de données SQLite
def init_db():
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_subscriber(chat_id):
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()

def remove_subscriber(chat_id):
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def get_all_subscribers():
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute("SELECT chat_id FROM subscribers")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# 📊 API Polymarket
def get_world_cup_odds():
    try:
        r = requests.get('https://gamma-api.polymarket.com/events/30615', timeout=30)
        data = r.json()
        markets = data['markets']
        teams = {}
        for market in markets:
            team = market.get("groupItemTitle", "")
            prices = market.get("outcomePrices", "[]")
            active = market.get("active", False)
            if team and active:
                price_list = j.loads(prices) if isinstance(prices, str) else prices
                if price_list:
                    prob = round(float(price_list[0]) * 100, 1)
                    teams[team] = prob
        return teams
    except Exception as e:
        print(f"Erreur API odds: {e}")
        return {}

def get_todays_matches():
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        r = requests.get(
            'https://gamma-api.polymarket.com/events/keyset?title_search=vs&limit=20&order=volume24hr&ascending=false',
            timeout=30
        )
        data = r.json()
        events = data.get('events', [])
        matches = []
        for event in events:
            slug = event.get('slug', '')
            title = event.get('title', '')
            if (today in slug and
                'more-markets' not in slug and
                'exact' not in slug and
                'fifwc' in slug and
                'vs' in title.lower()):
                markets = event.get('markets', [])
                match_data = {'title': title, 'slug': slug, 'teams': {}}
                for market in markets:
                    question = market.get('question', '')
                    prices = market.get('outcomePrices', '[]')
                    group_title = market.get('groupItemTitle', '')
                    if group_title and ('win' in question.lower() or 'winner' in question.lower()):
                        try:
                            price_list = j.loads(prices) if isinstance(prices, str) else prices
                            if price_list:
                                prob = round(float(price_list[0]) * 100, 1)
                                match_data['teams'][group_title] = prob
                        except:
                            continue
                if not match_data['teams']:
                    for market in markets[:1]:
                        outcomes = market.get('outcomes', '[]')
                        prices = market.get('outcomePrices', '[]')
                        try:
                            outcome_list = j.loads(outcomes) if isinstance(outcomes, str) else outcomes
                            price_list = j.loads(prices) if isinstance(prices, str) else prices
                            if outcome_list and price_list:
                                for i, outcome in enumerate(outcome_list):
                                    match_data['teams'][outcome] = round(float(price_list[i]) * 100, 1)
                        except:
                            continue
                if match_data['teams']:
                    matches.append(match_data)
        return matches
    except Exception as e:
        print(f"Erreur matchs: {e}")
        return []

def build_morning_message():
    """Construit le message du matin combiné"""
    today = datetime.now(BRASILIA_TZ).strftime("%d/%m/%Y")
    message = f"🌅 *Bom dia! Copa do Mundo — {today}*\n\n"

    # 1. Matchs du jour
    matches = get_todays_matches()
    if matches:
        message += "⚽ *Jogos de hoje:*\n"
        for match in matches[:4]:
            message += f"\n🏟 *{match['title']}*\n"
            teams = match['teams']
            for team, prob in sorted(teams.items(), key=lambda x: x[1], reverse=True):
                emoji = "✅" if prob == max(teams.values()) else "▪️"
                message += f"{emoji} {team}: *{prob}%*\n"
    else:
        message += "⚽ *Nenhum jogo hoje*\n"

    # 2. Cotes des favoris
    message += "\n🏆 *Top favoritos ao título:*\n"
    teams = get_world_cup_odds()
    sorted_teams = sorted(teams.items(), key=lambda x: x[1], reverse=True)[:5]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, (team, prob) in enumerate(sorted_teams):
        emoji = "🇧🇷 " if team == "Brazil" else ""
        message += f"{medals[i]} {emoji}{team}: *{prob}%*\n"

    # 3. Focus Brésil
    brasil_prob = teams.get("Brazil")
    if brasil_prob:
        gain = round(100 / brasil_prob * 100, 0)
        message += f"\n🇧🇷 *Brasil hoje:*\n"
        message += f"📊 Chance de ser campeão: *{brasil_prob}%*\n"
        message += f"💰 $100 apostados = *${gain:.0f}* se ganhar\n"

    message += "\n💡 Fonte: Polymarket — ao vivo"
    return message

# 🤖 Commandes Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    add_subscriber(chat_id)
    keyboard = [[InlineKeyboardButton("🚀 Começar a negociar no Polymarket", url=AFFILIATE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚽ Bem-vindo ao Football Prediction