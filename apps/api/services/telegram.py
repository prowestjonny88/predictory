import os
import logging
import asyncio
import httpx
from sqlalchemy.orm import Session
from db.models import ForecastRun, SKU

logger = logging.getLogger(__name__)

async def send_forecast_summary_to_telegram(run_id: int, db: Session):
    """
    Analyzes a completed forecast run and sends a summary to Telegram.
    This should be run as a background task.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Telegram credentials not found. Skipping notification.")
        return

    # 1. Fetch the run and lines
    run = db.query(ForecastRun).filter(ForecastRun.id == run_id).first()
    if not run:
        return

    run_date = str(run.forecast_date)
    
    # 2. Get top 3 items by total volume
    lines = sorted(run.lines, key=lambda l: l.total, reverse=True)
    top_lines = lines[:3]
    total_forecasted = sum(l.total for l in lines)
    
    # 3. Map SKU IDs to Names
    sku_ids = [l.sku_id for l in top_lines]
    skus = {sku.id: sku.name for sku in db.query(SKU).filter(SKU.id.in_(sku_ids)).all()}

    top_items = [
        {"sku_name": skus.get(l.sku_id, f"SKU #{l.sku_id}"), "total": l.total}
        for l in top_lines
    ]

    # 4. Construct Message
    message_lines = [
        f"🥐 *Predictory: Tomorrow's Forecast is Ready!* ({run_date})",
        "",
        "*Top Predicted Movers:*",
    ]
    
    for i, item in enumerate(top_items, 1):
        message_lines.append(f"{i}. {item['sku_name']} - {item['total']:.1f} units")

    message_lines.append("")
    message_lines.append(f"📊 *Total Volume:* {total_forecasted:.0f} units expected across all products.")
    
    # 5. Simple Ingredient Suggestions Based on Top Items
    ingredients = set()
    for item in top_items:
        name = item['sku_name'].lower()
        if "croissant" in name or "pastry" in name or "tart" in name:
            ingredients.update(["Butter", "Flour"])
        elif "bread" in name or "sourdough" in name or "loaf" in name:
            ingredients.update(["Flour", "Yeast"])
        elif "cake" in name or "eclair" in name:
            ingredients.update(["Sugar", "Eggs", "Dairy"])
        elif "coffee" in name or "latte" in name or "espresso" in name:
            ingredients.update(["Coffee Beans", "Milk"])

    SUPPLIERS = {
        "Butter": {"name": "DairyCorp Supplies", "phone": "+1-555-0192"},
        "Flour": {"name": "Golden Mills", "phone": "+1-555-0100"},
        "Yeast": {"name": "Golden Mills", "phone": "+1-555-0100"},
        "Sugar": {"name": "SweetLife Distributors", "phone": "+1-555-0284"},
        "Eggs": {"name": "Local Farm Fresh", "phone": "+1-555-0311"},
        "Dairy": {"name": "DairyCorp Supplies", "phone": "+1-555-0192"},
        "Coffee Beans": {"name": "Roastmasters Inc", "phone": "+1-555-0455"},
        "Milk": {"name": "DairyCorp Supplies", "phone": "+1-555-0192"},
    }

    if ingredients:
        ing_str = ", ".join(sorted(list(ingredients)))
        message_lines.append(f"💡 *Add on stock:* Ensure you have enough *{ing_str}* prepped tonight for tomorrow's top movers!")
        
        message_lines.append("")
        message_lines.append("📞 *Quick Supplier Contacts:*")
        contacted_suppliers = set()
        for ing in sorted(list(ingredients)):
            if ing in SUPPLIERS:
                sup = SUPPLIERS[ing]
                if sup["name"] not in contacted_suppliers:
                    message_lines.append(f"• {sup['name']}: `{sup['phone']}` (for {ing})")
                    contacted_suppliers.add(sup["name"])
    
    message = "\n".join(message_lines)
    
    # 6. Send via Telegram API
    chat_ids = [cid.strip() for cid in chat_id.split(",") if cid.strip()]
    
    async with httpx.AsyncClient() as client:
        for cid in chat_ids:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": cid,
                "text": message,
                "parse_mode": "Markdown"
            }
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info(f"Successfully sent Telegram notification to {cid}.")
            except Exception as e:
                logger.error(f"Failed to send Telegram notification to {cid}: {e}")
