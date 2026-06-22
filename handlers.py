from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import AFFILIATE_LINK
from database import (
    add_subscriber, remove_subscriber, get_all_subscribers,
    log_source, get_tracking_stats, get_subscriber_count, get_recent_subscribers, DB_PATH
)
from polymarket_api import get_world_cup_odds, get_todays_matches, get_next_brazil_match
from utils import get_share_button


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    add_subscriber(
        chat_id,
        first_name=user.first_name or "",
        username=user.username or "",
        language=user.language_code or ""
    )
    source = context.args[0] if context.args else "organic"
    log_source(chat_id, source)

    teams = get_world_cup_odds()
    brasil_prob = teams.get("Brazil", 6.7)
    keyboard = [
        [InlineKeyboardButton("🚀 Negociar no Polymarket AGORA", url=AFFILIATE_LINK)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    sent_message = await update.message.reply_text(
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
        f"👉 Toque no botao abaixo para negociar agora no Polymarket!\n\n"
        f"Compartilhe com seus amigos torcedores!",
        reply_markup=reply_markup
    )

    try:
        await context.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=sent_message.message_id,
            disable_notification=True
        )
    except Exception as e:
        print(f"Erreur pin: {e}")

async def alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers = get_all_subscribers()
    if chat_id in subscribers:
        remove_subscriber(chat_id)
        await update.message.reply_text("Alertas desativados. Use /alerta para reativar.")
    else:
        user = update.effective_user
        add_subscriber(
            chat_id,
            first_name=user.first_name or "",
            username=user.username or "",
            language=user.language_code or ""
        )
        await update.message.reply_text(
            "Alertas ativados! Voce recebera um resumo diario as 9h e alertas antes de cada jogo."
        )


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
    odds_url = f"https://polymarket.com/event/world-cup-winner?via=yZWX33z"
    keyboard = [
        [InlineKeyboardButton("Negociar agora", url=odds_url)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)


async def brasil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Buscando dados do Brasil...")
    teams = get_world_cup_odds()
    prob = teams.get("Brazil")
    sorted_teams = sorted(teams.items(), key=lambda x: x[1], reverse=True)
    position = next((i + 1 for i, (t, _) in enumerate(sorted_teams) if t == "Brazil"), "?")
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
    brasil_url = f"https://polymarket.com/event/world-cup-winner?via=yZWX33z"
    keyboard = [
        [InlineKeyboardButton("Apostar no Brasil agora", url=brasil_url)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup, disable_web_page_preview=True)


async def matchs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Buscando jogos de hoje...")
    matches = get_todays_matches()
    if matches:
        message = "*Jogos de hoje - Copa do Mundo 2026*\n\n"
        for match in matches[:5]:
            time_str = f" — {match['time']}" if match.get('time') else ""
            message += f"🏟 *{match['title']}*{time_str}\n"
            teams = match['teams']
            for team, prob in sorted(teams.items(), key=lambda x: x[1], reverse=True):
                emoji = "✅" if prob == max(teams.values()) else "▪️"
                message += f"{emoji} {team}: *{prob}%*\n"
            message += "\n"
        message += f"Fonte: [Polymarket](https://polymarket.com/sports?via=yZWX33z) - ao vivo"
    else:
        message = "Nenhum jogo encontrado para hoje."
    keyboard = []
    for match in matches[:5]:
        match_url = f"https://polymarket.com/event/{match['slug']}?via=yZWX33z"
        keyboard.append([InlineKeyboardButton(
            f"Negociar — {match['title']}",
            url=match_url
        )])
    keyboard.append([get_share_button()])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

async def proxjogo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Buscando proximo jogo do Brasil...")
    match_data = get_next_brazil_match()
    if match_data:
        message = f"🇧🇷 *Proximo jogo do Brasil*\n\n"
        message += f"🏟 *{match_data['title']}*\n\n"
        teams = match_data['teams']
        for team, prob in sorted(teams.items(), key=lambda x: x[1], reverse=True):
            emoji = "✅" if prob == max(teams.values()) else "▪️"
            message += f"{emoji} {team}: *{prob}%*\n"
        message += "\nFonte: Polymarket - ao vivo"
    else:
        message = "Nenhum jogo do Brasil encontrado no momento."
    keyboard = [
        [InlineKeyboardButton("Apostar no Brasil agora", url=AFFILIATE_LINK)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = get_subscriber_count()
    recent = get_recent_subscribers(5)
    tracking = get_tracking_stats()

    message = "*Estatisticas do bot*\n\n"
    message += f"Total de assinantes: *{total}*\n\n"
    message += "*Ultimos 5 inscritos:*\n"
    for first_name, username, language, joined_at in recent:
        user_str = f"@{username}" if username else first_name or "Unknown"
        message += f"▪ {user_str} ({language}) — {joined_at[:10]}\n"
    message += "\n*Origem dos usuarios:*\n"
    for source, count in tracking:
        message += f"▪ {source}: *{count}*\n"
    await update.message.reply_text(message)

ADMIN_USERNAME = "antoine7799"


async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text("Comando nao disponivel.")
        return

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT first_name, username, language, joined_at FROM subscribers ORDER BY joined_at DESC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Nenhum assinante.")
        return

    message = f"*Lista completa de assinantes ({len(rows)}):*\n\n"
    for first_name, username, language, joined_at in rows:
        user_str = f"@{username}" if username else (first_name or "Unknown")
        message += f"▪ {user_str} ({language}) — {joined_at[:10]}\n"

    if len(message) > 4000:
        message = message[:4000] + "\n\n... (lista truncada)"

    await update.message.reply_text(message, parse_mode="Markdown")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Como usar este bot:*\n\n"
        "/matchs - Jogos de hoje\n"
        "/brasil - Chances do Brasil ganhar\n"
        "/proxjogo - Proximo jogo do Brasil\n"
        "/odds - Top favoritos\n"
        "/alerta - Ativar/desativar alertas\n"
        "/stats - Estatisticas do bot\n\n"
        "Todos os dados sao em tempo real via Polymarket.",
        parse_mode="Markdown"
    )

async def daily_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text("Comando nao disponivel.")
        return
    from polymarket_api import build_morning_message, get_todays_matches
    message, matches = build_morning_message()

    keyboard = []
    for match in matches[:4]:
        match_url = f"https://polymarket.com/event/{match['slug']}?via=yZWX33z"
        keyboard.append([InlineKeyboardButton(
            f"Negociar — {match['title']}",
            url=match_url
        )])
    keyboard.append([get_share_button()])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text("Comando nao disponivel.")
        return
    
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    lines = list(conn.iterdump())
    conn.close()
    
    backup_text = "\n".join(lines)
    
    if len(backup_text) > 4000:
        chunks = [backup_text[i:i+4000] for i in range(0, len(backup_text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(f"```\n{chunk}\n```", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"```\n{backup_text}\n```", parse_mode="Markdown")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text("Comando nao disponivel.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /broadcast Votre message ici\n\n"
            "Exemple: /broadcast Brasil joga amanha! Confira as odds agora."
        )
        return

    message = " ".join(context.args)
    subscribers = get_all_subscribers()

    keyboard = [
        [InlineKeyboardButton("Ver no Polymarket", url=AFFILIATE_LINK)],
        [get_share_button()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    sent = 0
    failed = 0
    for chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup
            )
            sent += 1
        except Exception as e:
            print(f"Erreur broadcast {chat_id}: {e}")
            failed += 1

    await update.message.reply_text(
        f"Broadcast termine!\n✅ Envoye: {sent}\n❌ Echec: {failed}"
    )