from datetime import datetime
import json as j
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import AFFILIATE_LINK
from database import get_all_subscribers, is_alert_sent, mark_alert_sent, get_last_odds, update_odds
from polymarket_api import build_morning_message
from utils import get_share_button


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
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Erreur envoi {chat_id}: {e}")


async def check_upcoming_matches(context):
    try:
        r = requests.get(
            'https://gamma-api.polymarket.com/events/keyset?title_search=vs&limit=100&order=volume24hr&ascending=false',
            timeout=30
        )
        data = r.json()
        events = data.get('events', [])
        now = datetime.utcnow()

        for event in events:
            slug = event.get('slug', '')
            title = event.get('title', '')
            start_time_str = event.get('startTime', '')

            if not start_time_str or 'fifwc' not in slug or 'more-markets' in slug or 'exact' in slug:
                continue

            try:
                start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                continue

            diff_minutes = (start_time - now).total_seconds() / 60
            if not (45 <= diff_minutes <= 75):
                continue

            alert_slug = f"prematch_{slug}"
            if is_alert_sent(alert_slug):
                continue

            markets = event.get('markets', [])
            teams = {}
            for market in markets:
                question = market.get('question', '')
                prices = market.get('outcomePrices', '[]')
                group_title = market.get('groupItemTitle', '')
                if group_title and ('win' in question.lower() or 'winner' in question.lower()):
                    try:
                        price_list = j.loads(prices) if isinstance(prices, str) else prices
                        if price_list:
                            prob = round(float(price_list[0]) * 100, 1)
                            teams[group_title] = prob
                    except Exception:
                        continue

            if not teams:
                continue

            brazil_playing = "Brazil" in teams
            message = f"JOGO EM 1 HORA!\n\n"
            message += f"🏟 *{title}*\n\n"
            for team, prob in sorted(teams.items(), key=lambda x: x[1], reverse=True):
                emoji = "✅" if prob == max(teams.values()) else "▪️"
                br = "🇧🇷 " if team == "Brazil" else ""
                message += f"{emoji} {br}{team}: *{prob}%*\n"

            if brazil_playing:
                message += f"\nO Brasil joga agora! Aposte antes do apito!"
            else:
                message += f"\nNegocie antes do apito inicial!"

            subscribers = get_all_subscribers()
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
                    print(f"Erreur alerte {chat_id}: {e}")

            mark_alert_sent(alert_slug)
            print(f"Alerte envoyee pour {title}")

    except Exception as e:
        print(f"Erreur check_upcoming_matches: {e}")


async def check_odds_movement(context):
    try:
        r = requests.get(
            'https://gamma-api.polymarket.com/events/keyset?title_search=vs&limit=100&order=volume24hr&ascending=false',
            timeout=30
        )
        data = r.json()
        events = data.get('events', [])

        for event in events:
            slug = event.get('slug', '')
            title = event.get('title', '')

            if 'fifwc' not in slug or 'more-markets' in slug or 'exact' in slug:
                continue

            live = event.get('live', False)
            if not live:
                continue

            markets = event.get('markets', [])
            teams = {}
            for market in markets:
                question = market.get('question', '')
                prices = market.get('outcomePrices', '[]')
                group_title = market.get('groupItemTitle', '')
                if group_title and ('win' in question.lower() or 'winner' in question.lower()):
                    try:
                        price_list = j.loads(prices) if isinstance(prices, str) else prices
                        if price_list:
                            prob = round(float(price_list[0]) * 100, 1)
                            teams[group_title] = prob
                    except Exception:
                        continue

            if not teams:
                continue

            for team, current_prob in teams.items():
                last_prob = get_last_odds(slug, team)
                update_odds(slug, team, current_prob)

                if last_prob is None:
                    continue

                diff = current_prob - last_prob
                if abs(diff) < 8:
                    continue

                direction = "subiu" if diff > 0 else "caiu"
                emoji = "📈" if diff > 0 else "📉"

                message = f"{emoji} MOVIMENTO BRUSCO!\n\n"
                message += f"🏟 *{title}*\n\n"
                message += f"{team}: {last_prob}% para *{current_prob}%* ({direction} {abs(diff):.1f} pontos)\n\n"
                message += "Algo aconteceu no jogo! Confira agora"

                subscribers = get_all_subscribers()
                keyboard = [
                    [InlineKeyboardButton("Ver ao vivo", url=AFFILIATE_LINK)],
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
                        print(f"Erreur alerte mouvement {chat_id}: {e}")

                print(f"Alerte mouvement envoyee: {team} {direction} de {abs(diff)} points")

    except Exception as e:
        print(f"Erreur check_odds_movement: {e}")