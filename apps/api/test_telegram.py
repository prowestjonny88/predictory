import asyncio
from dotenv import load_dotenv

# Load env before importing other things
load_dotenv()

from db.database import SessionLocal
from db.models import ForecastRun
from services.telegram import send_forecast_summary_to_telegram

async def test_telegram():
    db = SessionLocal()
    try:
        # Get the latest forecast run
        latest_run = db.query(ForecastRun).order_by(ForecastRun.created_at.desc()).first()
        if not latest_run:
            print("No forecast runs found in the database. Please run a forecast first.")
            return
            
        print(f"Triggering telegram notification for ForecastRun ID: {latest_run.id}")
        await send_forecast_summary_to_telegram(latest_run.id, db)
        print("Done! Check your Telegram.")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_telegram())
