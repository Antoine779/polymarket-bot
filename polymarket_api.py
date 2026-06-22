import json as j
import requests
from datetime import datetime
from config import BRASILIA_TZ, WORLD_CUP_EVENT_ID, AFFILIATE_LINK


def get_world_cup_odds():
    try:
        r = requests.get(f'https://gamma-api.polymarket.com/events/{WORLD_CUP_EVENT_ID}', timeout=30)
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
                        except Exception:
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
                        except Exception:
                            continue
                if match_data['teams']:
                    matches.append(match_data)
        return matches
    except Exception as e:
        print(f"Erreur matchs: {e}")
        return []


def get_next_brazil_match():
    try:
        r = requests.get(
            'https://gamma-api.polymarket.com/events/keyset?title_search=Brazil&limit=10&order=volume24hr&ascending=false',
            timeout=30
        )
        data = r.json()
        events = data.get('events', [])
        for event in events:
            slug = event.get('slug', '')
            if 'fifwc' in slug and 'brazil' in slug.lower() and 'more-markets' not in slug and 'exact' not in slug:
                markets = event.get('markets', [])
                match_data = {'title': event['title'], 'teams': {}}
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
                        except Exception:
                            continue
                if match_data['teams']:
                    return match_data
        return None
    except Exception as e:
        print(f"Erreur proxjogo: {e}")
        return None


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

    message += f"\nFonte: [Polymarket]({AFFILIATE_LINK}) - ao vivo"
    return message