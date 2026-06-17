import os
import json as j
import sqlite3
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pytz

# Token et lien affilié
TOKEN = os.environ.get("TOKEN")
AFFILIATE_LINK = "https://polymarket.com?via=yZWX33z"
BRASILIA_TZ = pytz.timezone("America/Sao_Paulo")

# Base de données SQLite
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

# Bouton partager
def get_share_button():
    return InlineKeyboardButton(
        "Compartilhar com amigos",
        url="https://t.me/share/url?url=t.me/FootballPredictionBrazil_bot&text=Bot+gratuito+com+probabilidades+ao+vivo+da+Copa+do+Mundo+2026!"
    )

# API Polymarket
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
    today = datetime.now(BRASILIA_TZ).strftime("%d/%m/%Y")
    message = f"Bom dia! Copa do Mundo - {today}\n\n"
    matches = get_todays_matches()
    if matches:
        message += "Jogos de hoje:\n"
        for match in matches[:4]:
            message += f"\n🏟 *{match['title']}*\n"
            teams = match['teams']
            for team, prob in sorted(teams.items(), key=lambda x: x[1], reverse=True):
                emoji = "✅" if prob == max(teams.values()) else "▪️"
                message += f"{emoji} {team}: *{prob}%*\n"
    else:
        message += "Nenhum jogo hoje\n"
    message += "\n*Top favoritos ao titulo:*\n"
    teams = get_world_cup_odds()
    sorted_teams = sorted(teams.items(), key=lambda x: x[1], reverse=True)[:5]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, (team, prob) in enumerate(sorted_teams):
        emoji = "🇧🇷 " if team == "Brazil" else ""
        message += f"{medals[i]} {emoji}{team}: *{prob}%*\n"
    brasil_prob = teams.get("Brazil")
    if brasil_prob:
        gain = round(100 / brasil_prob * 100, 0)
        message += f"\n🇧🇷 *Brasil hoje:*\n"
        message += f"Chance de ser campeao: *{brasil_prob}%*\n"
        message += f"$100 apostados = *${gain:.0f}* se ganhar\n"
    message += "\nFonte: Polymarket - ao vivo"
    return message

# Commandes Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    add_subscriber(chat_id)
    teams = get_world_cup_odds()
    brasil_prob = teams.get("Brazil", 6.7)
    keyboard = [
        [InlineKeyboardButton("Negociar no Polymarket", url=AFFILIATE_LINK)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"O Brasil tem apenas {brasil_prob}% de chance de ganhar a Copa "
        f"segundo o maior mercado de previsao do mundo.\n\n"
        f"Voce acha que estao subestimados?\n\n"
        f"Este bot te da probabilidades ao vivo antes de cada jogo, "
        f"alertas diarios as 9h e as chances reais do Brasil ganhar.\n\n"
        f"Comandos:\n"
        f"/matchs - Jogos de hoje\n"
        f"/brasil - Chances do Brasil\n"
        f"/proxjogo - Proximo jogo do Brasil\n"
        f"/odds - Top favoritos\n"
        f"/alerta - Alertas diarios\n\n"
        f"Compartilhe com seus amigos torcedores!",
        reply_markup=reply_markup
    )

async def alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers = get_all_subscribers()
    if chat_id in subscribers:
        remove_subscriber(chat_id)
        await update.message.reply_text("Alertas desativados. Use /alerta para reativar.")
    else:
        add_subscriber(chat_id)
        await update.message.reply_text("Alertas ativados! Voce recebera um resumo diario as 9h.")

async def odds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Buscando probabilidades ao vivo...")
    teams = get_world_cup_odds()
    sorted_teams = sorted(teams.items(), key=lambda x: x[1], reverse=True)[:8]
    if sorted_teams:
        message = "*Probabilidades ao vivo - Copa do Mundo 2026*\n\n"
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        for i, (team, prob) in enumerate(sorted_teams):
            emoji = "🇧🇷 " if team == "Brazil" else ""
            message += f"{medals[i]} {emoji}{team}: *{prob}%*\n"
        message += "\nFonte: Polymarket - ao vivo"
    else:
        message = "Dados temporariamente indisponiveis. Tente novamente."
    keyboard = [
        [InlineKeyboardButton("Negociar agora", url=AFFILIATE_LINK)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def brasil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Buscando dados do Brasil...")
    teams = get_world_cup_odds()
    prob = teams.get("Brazil")
    sorted_teams = sorted(teams.items(), key=lambda x: x[1], reverse=True)
    position = next((i+1 for i, (t, _) in enumerate(sorted_teams) if t == "Brazil"), "?")
    if prob:
        gain = round(100 / prob * 100, 0)
        message = (
            f"🇧🇷 *Brasil na Copa do Mundo 2026*\n\n"
            f"Posicao atual: *{position}o favorito*\n"
            f"Chance de ser campeao: *{prob}%*\n\n"
            f"Se voce apostar $100 agora e o Brasil ganhar,\n"
            f"voce recebe *${gain:.0f}*\n\n"
            f"Dados em tempo real via Polymarket"
        )
    else:
        message = "🇧🇷 *Brasil na Copa do Mundo 2026*\n\nDados temporariamente indisponiveis."
    keyboard = [
        [InlineKeyboardButton("Apostar no Brasil agora", url=AFFILIATE_LINK)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def matchs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Buscando jogos de hoje...")
    matches = get_todays_matches()
    if matches:
        message = "*Jogos de hoje - Copa do Mundo 2026*\n\n"
        for match in matches[:5]:
            message += f"🏟 *{match['title']}*\n"
            teams = match['teams']
            for team, prob in sorted(teams.items(), key=lambda x: x[1], reverse=True):
                emoji = "✅" if prob == max(teams.values()) else "▪️"
                message += f"{emoji} {team}: *{prob}%*\n"
            message += "\n"
        message += "Fonte: Polymarket - ao vivo"
    else:
        message = "Nenhum jogo encontrado para hoje."
    keyboard = [
        [InlineKeyboardButton("Negociar agora", url=AFFILIATE_LINK)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def proxjogo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Buscando proximo jogo do Brasil...")
    try:
        r = requests.get(
            'https://gamma-api.polymarket.com/events/keyset?title_search=Brazil&limit=10&order=volume24hr&ascending=false',
            timeout=30
        )
        data = r.json()
        events = data.get('events', [])
        brazil_match = None
        for event in events:
            slug = event.get('slug', '')
            title = event.get('title', '')
            if 'fifwc' in slug and 'brazil' in slug.lower() and 'more-markets' not in slug and 'exact' not in slug:
                brazil_match = event
                break
        if brazil_match:
            markets = brazil_match.get('markets', [])
            match_data = {'title': brazil_match['title'], 'teams': {}}
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
            if match_data['teams']:
                message = f"🇧🇷 *Proximo jogo do Brasil*\n\n"
                message += f"🏟 *{match_data['title']}*\n\n"
                teams = match_data['teams']
                for team, prob in sorted(teams.items(), key=lambda x: x[1], reverse=True):
                    emoji = "✅" if prob == max(teams.values()) else "▪️"
                    message += f"{emoji} {team}: *{prob}%*\n"
                message += "\nFonte: Polymarket - ao vivo"
            else:
                message = "Dados do proximo jogo do Brasil nao disponiveis ainda."
        else:
            message = "Nenhum jogo do Brasil encontrado no momento."
    except Exception as e:
        print(f"Erreur proxjogo: {e}")
        message = "Erro ao buscar dados. Tente novamente."
    keyboard = [
        [InlineKeyboardButton("Apostar no Brasil agora", url=AFFILIATE_LINK)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Como usar este bot:*\n\n"
        "/matchs - Jogos de hoje\n"
        "/brasil - Chances do Brasil ganhar\n"
        "/proxjogo - Proximo jogo do Brasil\n"
        "/odds - Top favoritos\n"
        "/alerta - Ativar/desativar alertas diarios\n\n"
        "Todos os dados sao em tempo real via Polymarket.",
        parse_mode="Markdown"
    )

async def send_morning_alert(context):
    subscribers = get_all_subscribers()
    if not subscribers:
        return
    message = build_morning_message()
    keyboard = [
        [InlineKeyboardButton("Negociar agora", url=AFFILIATE_LINK)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    for chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Erreur envoi {chat_id}: {e}")

if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("odds", odds))
    app.add_handler(CommandHandler("brasil", brasil))
    app.add_handler(CommandHandler("matchs", matchs))
    app.add_handler(CommandHandler("proxjogo", proxjogo))
    app.add_handler(CommandHandler("alerta", alerta))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.job_queue.run_daily(
        send_morning_alert,
        time=datetime.strptime("12:00", "%H:%M").time().replace(tzinfo=pytz.utc)
    )
    print("Bot demarre avec toutes les fonctionnalites !")
    app.run_polling()