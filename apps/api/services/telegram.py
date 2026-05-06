import os
import logging
import httpx
from db.database import SessionLocal
from db.models import ForecastRun, SKU

logger = logging.getLogger(__name__)


async def send_forecast_summary_to_telegram(run_id: int, db=None):
    """
    Analyzes a completed forecast run and sends a summary to Telegram.
    This should be run as a FastAPI BackgroundTask.

    IMPORTANT: We intentionally open a *new* DB session here rather than
    reusing the request-scoped session passed in from the router.  FastAPI
    closes the Depends(get_db) session as soon as the HTTP response is sent,
    which happens *before* background tasks execute — so any query through
    the original session would silently return nothing.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Telegram credentials not found. Skipping notification.")
        return

    db = SessionLocal()
    try:
        # 1. Fetch the run and its lines
        run = db.query(ForecastRun).filter(ForecastRun.id == run_id).first()
        if not run:
            logger.warning(f"Telegram: ForecastRun {run_id} not found.")
            return

        run_date = str(run.forecast_date)

        # 2. Rank lines by total volume, take top 3
        lines = sorted(run.lines, key=lambda l: l.total, reverse=True)
        top_lines = lines[:3]
        total_forecasted = sum(l.total for l in lines)

        # 3. Resolve SKU names
        sku_ids = [l.sku_id for l in top_lines]
        skus = {sku.id: sku.name for sku in db.query(SKU).filter(SKU.id.in_(sku_ids)).all()}

        top_items = [
            {"sku_name": skus.get(l.sku_id, f"SKU #{l.sku_id}"), "total": l.total}
            for l in top_lines
        ]

        # 4. Build the message
        message_lines = [
            f"🥐 *Predictory: Tomorrow's Forecast is Ready!* ({run_date})",
            "",
            "*Top Predicted Movers:*",
        ]

        for i, item in enumerate(top_items, 1):
            message_lines.append(f"{i}. {item['sku_name']} - {item['total']:.1f} units")

        message_lines.append("")
        message_lines.append(
            f"📊 *Total Volume:* {total_forecasted:.0f} units expected across all products."
        )

        # 5. Ingredient suggestions
        SUPPLIERS = {
            "Butter":       {"name": "DairyCorp Supplies",      "phone": "+1-555-0192"},
            "Flour":        {"name": "Golden Mills",             "phone": "+1-555-0100"},
            "Yeast":        {"name": "Golden Mills",             "phone": "+1-555-0100"},
            "Sugar":        {"name": "SweetLife Distributors",   "phone": "+1-555-0284"},
            "Eggs":         {"name": "Local Farm Fresh",         "phone": "+1-555-0311"},
            "Dairy":        {"name": "DairyCorp Supplies",       "phone": "+1-555-0192"},
            "Coffee Beans": {"name": "Roastmasters Inc",         "phone": "+1-555-0455"},
            "Milk":         {"name": "DairyCorp Supplies",       "phone": "+1-555-0192"},
        }

        ingredients: set[str] = set()
        for item in top_items:
            name = item["sku_name"].lower()
            if any(k in name for k in ("croissant", "pastry", "tart")):
                ingredients.update(["Butter", "Flour"])
            elif any(k in name for k in ("bread", "sourdough", "loaf")):
                ingredients.update(["Flour", "Yeast"])
            elif any(k in name for k in ("cake", "eclair")):
                ingredients.update(["Sugar", "Eggs", "Dairy"])
            elif any(k in name for k in ("coffee", "latte", "espresso")):
                ingredients.update(["Coffee Beans", "Milk"])

        if ingredients:
            ing_str = ", ".join(sorted(ingredients))
            message_lines.append(
                f"💡 *Add on stock:* Ensure you have enough *{ing_str}* prepped tonight!"
            )
            message_lines.append("")
            message_lines.append("📞 *Quick Supplier Contacts:*")
            seen: set[str] = set()
            for ing in sorted(ingredients):
                if ing in SUPPLIERS:
                    sup = SUPPLIERS[ing]
                    if sup["name"] not in seen:
                        message_lines.append(
                            f"• {sup['name']}: `{sup['phone']}` (for {ing})"
                        )
                        seen.add(sup["name"])

        message = "\n".join(message_lines)

        # 6. Deliver to every configured Chat ID
        chat_ids = [cid.strip() for cid in chat_id.split(",") if cid.strip()]
        async with httpx.AsyncClient() as client:
            for cid in chat_ids:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {"chat_id": cid, "text": message, "parse_mode": "Markdown"}
                try:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    logger.info(f"Telegram notification sent to {cid}.")
                except Exception as exc:
                    logger.error(f"Failed to send Telegram notification to {cid}: {exc}")

    except Exception as exc:
        logger.error(f"Unexpected error in Telegram background task: {exc}")
    finally:
        db.close()
