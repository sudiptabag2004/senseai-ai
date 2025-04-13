from apscheduler.schedulers.asyncio import AsyncIOScheduler
from api.db import publish_scheduled_tasks

scheduler = AsyncIOScheduler()


# Check for tasks to publish every minute
@scheduler.scheduled_job("interval", minutes=1)
async def check_scheduled_tasks():
    await publish_scheduled_tasks()


# Start the scheduler
# scheduler.start()
