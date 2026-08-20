import os
import discord
from discord.ext import commands
import time
from dotenv import load_dotenv

from brain import generate_response

load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")
OWNER_ID_STR = os.environ.get("OWNER_ID")
OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR else None

# Setup intent
intents = discord.Intents.default()
intents.message_content = True

class IlseBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced.")

bot = IlseBot()

TEST_SERVER_ID = 1537631696743174224

def is_owner_or_authorized(user):
    if OWNER_ID:
        return user.id == OWNER_ID
    return True # If no OWNER_ID is set, just allow the command and they can add it later

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print(f"Restricted to Test Server ID: {TEST_SERVER_ID}")
    if OWNER_ID:
        print(f"Authorized User ID: {OWNER_ID}")
    else:
        print("WARNING: OWNER_ID is not set in .env. Anyone in the test server can use the bot.")
    print("Bot is ready and running in terminal.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check authorized user
    if not is_owner_or_authorized(message.author):
        return

    # Restrict to test server only
    guild_id = message.guild.id if message.guild else None
    if guild_id != TEST_SERVER_ID:
        return

    # Only respond to mentions
    if bot.user in message.mentions:
        print(f"[{time.strftime('%X')}] Received mention from {message.author.name}. Generating response...")
        wait_msg = await message.reply("*(Ilse is reviewing her documents...)*")
        
        async with message.channel.typing():
            chat_history = ""
            # Fetch last 5 messages for context
            async for msg in message.channel.history(limit=5, before=message):
                # reverse order to read top down
                chat_history = f"{msg.author.name}: {msg.content}\n" + chat_history
            
            response = await generate_response(message.content, chat_history, is_test_server=True)
            
            # Chunk response if > 2000 chars
            if len(response) > 2000:
                await wait_msg.edit(content=response[:1900])
                for chunk in [response[i:i+1900] for i in range(1900, len(response), 1900)]:
                    await message.channel.send(chunk)
            else:
                await wait_msg.edit(content=response)
        
        print(f"[{time.strftime('%X')}] Response to {message.author.name} completed.")

@bot.tree.command(name="analyze", description="Run a deep analysis on a topic using the wiki or databases.")
async def analyze_command(interaction: discord.Interaction, query: str):
    if not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("You are not authorized to use this bot.", ephemeral=True)
        return
        
    guild_id = interaction.guild.id if interaction.guild else None
    if guild_id != TEST_SERVER_ID:
        await interaction.response.send_message("I am currently restricted to the test server.", ephemeral=True)
        return

    # Acknowledge the interaction immediately to prevent the 3-second timeout
    await interaction.response.defer(thinking=True)
    print(f"[{time.strftime('%X')}] Received /analyze command from {interaction.user.name}. Query: {query}")
    
    chat_history = f"System: The user invoked an explicit analysis slash command with query: {query}"
    
    response = await generate_response(query, chat_history, is_test_server=True)
    
    if len(response) > 2000:
        for i, chunk in enumerate([response[j:j+1900] for j in range(0, len(response), 1900)]):
            if i == 0:
                await interaction.followup.send(chunk)
            else:
                await interaction.channel.send(chunk)
    else:
        await interaction.followup.send(response)
        
    print(f"[{time.strftime('%X')}] /analyze response to {interaction.user.name} completed.")

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN is not set in .env")
    else:
        bot.run(TOKEN)
