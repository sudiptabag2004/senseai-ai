from apscheduler.schedulers.asyncio import AsyncIOScheduler
from api.db import publish_scheduled_tasks

scheduler = AsyncIOScheduler()


# Check for tasks to publish every minute
@scheduler.scheduled_job("interval", minutes=1)
async def check_scheduled_tasks():
    published_task_ids = await publish_scheduled_tasks()
    if published_task_ids:
        print(f"Published tasks: {published_task_ids}")
    else:
        print("No tasks to publish")


# Start the scheduler
# scheduler.start()
