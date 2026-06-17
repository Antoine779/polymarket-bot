import os
import json as j
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 🔑 Ton token BotFather
TOKEN = os.environ.get("TOKEN")

# 🔗 Ton lien affilié Brésil
AFFILIATE_LINK = "https://polymarket.com?via=yZWX33z"

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
        print(f"Erreur API: {e}")
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
            if today in slug and 'more-markets' not in slug and 'vs' in title.lower():
                markets = event.get('markets', [])
                match_data = {'title': title, 'slug': slug, 'odds': {}}
                for market in markets:
                    prices = market.get('outcomePrices', '[]')
                    outcomes = market.get('outcomes', '[]')
                    try:
                        price_list = j.loads(prices) if isinstance(prices, str) else prices
                        outcome_list = j.loads(outcomes) if isinstance(outcomes, str) else outcomes
                        if price_list and outcome_list:
                            for i, outcome in enumerate(outcome_list):
                                match_data['odds'][outcome] = round(float(price_list[i]) * 100, 1)
                    except:
                        continue
                if match_data['odds']:
                    matches.append(match_data)
        return matches
    except Exception as e:
        print(f"Erreur matchs: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 Começar a negociar no Polymarket", url=AFFILIATE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚽ Bem-vindo ao Football Prediction Brazil Bot!\n\n"
        "🇧🇷 Negocie nos mercados de predição da Copa do Mundo 2026.\n\n"
        "📊 Comandos disponíveis:\n"
        "/odds — Ver probabilidades ao vivo\n"
        "/brasil — Chances do Brasil ganhar\n"
        "/matchs — Jogos de hoje\n"
        "/ajuda — Ajuda\n\n"
        "Clique abaixo para começar 👇",
        reply_markup=reply_markup
    )

async def odds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Buscando probabilidades ao vivo...")
    teams = get_world_cup_odds()
    sorted_teams = sorted(teams.items(), key=lambda x: x[1], reverse=True)[:8]
    if sorted_teams:
        message = "📊 *Probabilidades ao vivo — Copa do Mundo 2026*\n\n"
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        for i, (team, prob) in enumerate(sorted_teams):
            emoji = "🇧🇷 " if team == "Brazil" else ""
            message += f"{medals[i]} {emoji}{team}: *{prob}%*\n"
        message += "\n💡 Fonte: Polymarket — ao vivo"
    else:
        message = "⚠️ Dados temporariamente indisponíveis. Tente novamente."
    keyboard = [[InlineKeyboardButton("🚀 Negociar agora", url=AFFILIATE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def brasil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Buscando dados do Brasil...")
    teams = get_world_cup_odds()
    prob = teams.get("Brazil")
    if prob:
        gain = round(100 / prob * 100, 0)
        message = (
            f"🇧🇷 *Brasil na Copa do Mundo 2026*\n\n"
            f"📊 Probabilidade de ser campeão: *{prob}%*\n\n"
            f"💰 Se você apostar $100 agora e o Brasil ganhar,\n"
            f"você recebe *${gain:.0f}*\n\n"
            f"📈 Dados em tempo real via Polymarket"
        )
    else:
        message = "🇧🇷 *Brasil na Copa do Mundo 2026*\n\n⚠️ Dados temporariamente indisponíveis.\nConsulte diretamente no Polymarket 👇"
    keyboard = [[InlineKeyboardButton("🚀 Apostar no Brasil agora", url=AFFILIATE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def matchs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Buscando jogos de hoje...")
    matches = get_todays_matches()
    if matches:
        message = "⚽ *Jogos de hoje — Copa do Mundo 2026*\n\n"
        for match in matches[:5]:
            message += f"🏟 *{match['title']}*\n"
            odds = match['odds']
            for outcome, prob in odds.items():
                emoji = "✅" if prob == max(odds.values()) else "▪️"
                message += f"{emoji} {outcome}: *{prob}%*\n"
            message += "\n"
        message += "💡 Fonte: Polymarket — ao vivo"
    else:
        message = "⚠️ Nenhum jogo encontrado para hoje."
    keyboard = [[InlineKeyboardButton("🚀 Negociar agora", url=AFFILIATE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Como usar este bot:*\n\n"
        "/odds — Probabilidades dos favoritos\n"
        "/brasil — Chances do Brasil ganhar\n"
        "/matchs — Jogos de hoje\n"
        "/start — Mensagem de boas-vindas\n\n"
        "🔎 Todos os dados são em tempo real via Polymarket.",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("odds", odds))
    app.add_handler(CommandHandler("brasil", brasil))
    app.add_handler(CommandHandler("matchs", matchs))
    app.add_handler(CommandHandler("ajuda", ajuda))
    print("✅ Bot démarré avec cotes en temps réel !")
    app.run_polling()