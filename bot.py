from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests

# 🔑 Ton token BotFather
TOKEN = "8996255916:AAG1raxOz3lIXrV49QGpS2QM9VkWL0u9PBI"

# 🔗 Ton lien affilié Brésil
AFFILIATE_LINK = "https://polymarket.com?via=yZWX33z"

def get_world_cup_odds():
    """Récupère les cotes depuis Polymarket"""
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
                import json
                price_list = json.loads(prices) if isinstance(prices, str) else prices
                if price_list:
                    prob = round(float(price_list[0]) * 100, 1)
                    teams[team] = prob
        return teams
    except Exception as e:
        print(f"Erreur API: {e}")
        return {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 Começar a negociar no Polymarket", url=AFFILIATE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚽ Bem-vindo ao Football Prediction Brazil Bot!\n\n"
        "🇧🇷 Negocie nos mercados de predição da Copa do Mundo 2026.\n\n"
        "📊 Comandos disponíveis:\n"
        "/odds — Ver probabilidades ao vivo\n"
        "/brasil — Chances do Brasil ganhar\n"
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
        message = (
            "🇧🇷 *Brasil na Copa do Mundo 2026*\n\n"
            "⚠️ Dados temporariamente indisponíveis.\n"
            "Consulte diretamente no Polymarket 👇"
        )
    
    keyboard = [[InlineKeyboardButton("🚀 Apostar no Brasil agora", url=AFFILIATE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Como usar este bot:*\n\n"
        "/odds — Probabilidades dos favoritos\n"
        "/brasil — Chances do Brasil ganhar\n"
        "/start — Mensagem de boas-vindas\n\n"
        "🔎 Todos os dados são em tempo real via Polymarket.",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("odds", odds))
    app.add_handler(CommandHandler("brasil", brasil))
    app.add_handler(CommandHandler("ajuda", ajuda))
    print("✅ Bot démarré avec cotes en temps réel !")
    app.run_polling()