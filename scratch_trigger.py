import asyncio
import discord
import os
import sys
import sqlite3
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
import auto_scraper

load_dotenv("config/.env")
TOKEN = os.getenv("DISCORD_TOKEN")

class DummyBot(discord.Client):
    async def on_ready(self):
        print("Bot ready, running scraper...")
        await auto_scraper.check_and_update_bills(self)
        await self.close()

intents = discord.Intents.default()
intents.message_content = True
bot = DummyBot(intents=intents)
bot.run(TOKEN)
