# app.py

import asyncio
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from commands.slack_commands import register_commands
from tasks.scheduled_tasks import daily_refresh_task
from utils.logging_utils import setup_logging
from cachetools import TTLCache
setup_logging()

app = AsyncApp(token=SLACK_BOT_TOKEN)
register_commands(app)
app.cache = TTLCache(maxsize=1000, ttl=3600)  # Adjust maxsize and ttl as needed

async def main():
    # Start the Slack app
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

    # Start the scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        daily_refresh_task,
        CronTrigger(hour=21, minute=3, timezone='UTC'),
        args=[app]  # Pass the app instance to the scheduled task
    )
    scheduler.start()

    # Start the handler
    await handler.start_async()

if __name__ == "__main__":
    asyncio.run(main())