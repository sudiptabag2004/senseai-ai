from apscheduler.schedulers.asyncio import AsyncIOScheduler
from api.db import publish_scheduled_tasks
from api.cron import send_usage_summary_stats
from api.settings import settings

scheduler = AsyncIOScheduler()


# Check for tasks to publish every minute
@scheduler.scheduled_job("interval", minutes=1)
async def check_scheduled_tasks():
    await publish_scheduled_tasks()


# Send usage summary stats every day at 9 AM
@scheduler.scheduled_job("cron", hour=9, minute=0)
async def daily_usage_stats():
    if not settings.slack_usage_stats_webhook_url:
        return

    await send_usage_summary_stats()
