from datetime import datetime
import pytz
from telegram.ext import ApplicationBuilder, CommandHandler

from config import TOKEN
from database import init_db
from handlers import start, odds, brasil, matchs, proxjogo, alerta, stats, ajuda, listusers, daily_alert
from alerts import send_morning_alert, check_upcoming_matches, check_odds_movement

if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("odds", odds))
    app.add_handler(CommandHandler("brasil", brasil))
    app.add_handler(CommandHandler("matchs", matchs))
    app.add_handler(CommandHandler("proxjogo", proxjogo))
    app.add_handler(CommandHandler("alerta", alerta))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("listusers", listusers))
    app.add_handler(CommandHandler("daily_alert", daily_alert))

    app.job_queue.run_daily(
        send_morning_alert,
        time=datetime.strptime("14:30", "%H:%M").time().replace(tzinfo=pytz.utc)
    )
    app.job_queue.run_repeating(check_upcoming_matches, interval=900, first=10)
    app.job_queue.run_repeating(check_odds_movement, interval=300, first=15)

    print("Bot demarre avec toutes les fonctionnalites!")
    app.run_polling()