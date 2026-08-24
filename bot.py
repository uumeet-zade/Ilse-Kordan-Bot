import os
import json
import discord
from discord.ext import commands, tasks
import time
from dotenv import load_dotenv

from brain import generate_response
import auto_scraper

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
CAPRICA_SERVER_ID = 1189603606568108103
ALLOWED_CAPRICA_CHANNELS = [1266040682213281955]

# --- Anti-Spam & Blacklist System ---
BLACKLIST_FILE = "blacklist.json"
user_last_ping = {} # {user_id: timestamp}
user_spam_strikes = {} # {user_id: count}
user_behavior_strikes = {} # {user_id: count}
COOLDOWN_SECONDS = 3
api_exhausted_until = 0

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {int(uid): None for uid in data}
                else:
                    return {int(k): v for k, v in data.items()}
        except:
            return {}
    return {}

def save_blacklist(bl):
    with open(BLACKLIST_FILE, "w") as f:
        json.dump(bl, f)

banned_users = load_blacklist()

def ban_user(user_id, duration_hours=None):
    expiry = time.time() + duration_hours * 3600 if duration_hours else None
    banned_users[user_id] = expiry
    save_blacklist(banned_users)
    if duration_hours:
        print(f"[{time.strftime('%X')}] [BANNED] User ID {user_id} has been temporarily blacklisted for {duration_hours} hours.")
    else:
        print(f"[{time.strftime('%X')}] [BANNED] User ID {user_id} has been permanently blacklisted.")

def is_banned(user_id):
    if user_id in banned_users:
        expiry = banned_users[user_id]
        if expiry is not None and time.time() > expiry:
            del banned_users[user_id]
            save_blacklist(banned_users)
            return False
        return True
    return False

AUTHORIZED_USERS = {610453628657860654} # Lyn

def is_owner_or_authorized(user):
    if OWNER_ID:
        if user.id == OWNER_ID or user.id in AUTHORIZED_USERS:
            return True
        return False
    return True

def is_allowed_channel(message):
    guild_id = message.guild.id if message.guild else None
    if guild_id == TEST_SERVER_ID:
        return True
    if guild_id == CAPRICA_SERVER_ID and message.channel.id in ALLOWED_CAPRICA_CHANNELS:
        return True
    return False
@tasks.loop(hours=24)
async def daily_bill_update():
    await auto_scraper.check_and_update_bills(bot)
    await auto_scraper.check_regional_bills(bot)
    await auto_scraper.scrape_lore_channels(bot)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print(f"Restricted to Test Server & Caprica Channel {ALLOWED_CAPRICA_CHANNELS[0]}")
    if OWNER_ID:
        print(f"Authorized Owner ID: {OWNER_ID}")
    print(f"Loaded {len(banned_users)} banned users.")
    print("Bot is ready and running in terminal.")
    
    if not daily_bill_update.is_running():
        daily_bill_update.start()

@bot.event
async def on_message(message):
    global api_exhausted_until

    if message.author == bot.user:
        return

    # Check API Exhaustion State
    if time.time() < api_exhausted_until:
        return

    # 1. Check Blacklist
    if is_banned(message.author.id):
        return

    # 2. Check Allowed Channel
    if not is_allowed_channel(message):
        return

    # 3. Handle Mentions
    if bot.user in message.mentions:
        # Check Cooldown
        if not is_owner_or_authorized(message.author):
            now = time.time()
            if message.author.id in user_last_ping:
                if now - user_last_ping[message.author.id] < COOLDOWN_SECONDS:
                    # Strike for spamming
                    user_spam_strikes[message.author.id] = user_spam_strikes.get(message.author.id, 0) + 1
                    if user_spam_strikes[message.author.id] >= 3:
                        ban_user(message.author.id)
                        await message.reply("You have been permanently ignored for spamming.")
                    else:
                        await message.reply(f"Please wait a moment before asking another question. (Strike {user_spam_strikes[message.author.id]}/3)", delete_after=5)
                    return
                    
            user_last_ping[message.author.id] = now

        print(f"[{time.strftime('%X')}] Received mention from {message.author.name}. Generating response...")
        wait_msg = await message.reply("*(Ilse is reviewing her documents...)*")
        
        async with message.channel.typing():
            chat_history = ""
            async for msg in message.channel.history(limit=15, before=message):
                chat_history = f"{msg.author.name} (ID: {msg.author.id}): {msg.content}\n" + chat_history
            
            is_test = (message.guild.id == TEST_SERVER_ID) if message.guild else False
            current_user_context = f"{message.author.name} (ID: {message.author.id})"
            
            response = await generate_response(message.content, chat_history, is_test_server=is_test, current_user=current_user_context)
            
            # Check API Exhaustion
            if response == "<API_EXHAUSTED>":
                api_exhausted_until = time.time() + 60
                await wait_msg.edit(content="*(Ilse enters a state of rest. I have run out of API tokens and will ignore all requests for the next minute while my quota refreshes.)*")
                return

            if "<IGNORE>" in response:
                await wait_msg.delete()
                return
                
            # Check for AI-driven Ban
            if "<BLOCK_USER>" in response:
                if not is_owner_or_authorized(message.author):
                    ban_user(message.author.id)
                    await wait_msg.delete()
                    await message.channel.send(f"I will not tolerate this conduct, {message.author.mention}.")
                    return
                else:
                    response = response.replace("<BLOCK_USER>", "")
                    
            # Check for AI-driven Strike (Slurs/Inappropriate)
            if "<STRIKE_USER>" in response:
                if not is_owner_or_authorized(message.author):
                    user_behavior_strikes[message.author.id] = user_behavior_strikes.get(message.author.id, 0) + 1
                    if user_behavior_strikes[message.author.id] >= 3:
                        ban_user(message.author.id)
                        await wait_msg.delete()
                        await message.channel.send(f"You have been permanently banned for repeated infractions, {message.author.mention}.")
                        return
                    else:
                        await wait_msg.delete()
                        await message.channel.send(f"I will not tolerate slurs, inappropriate conduct, or flirting, {message.author.mention}. (Strike {user_behavior_strikes[message.author.id]}/3)")
                        return
                else:
                    response = response.replace("<STRIKE_USER>", "")
            
            # Chunk response if > 2000 chars
            if len(response) > 2000:
                await wait_msg.edit(content=response[:1900])
                for chunk in [response[i:i+1900] for i in range(1900, len(response), 1900)]:
                    await message.channel.send(chunk)
            else:
                await wait_msg.edit(content=response)
        
        print(f"[{time.strftime('%X')}] Response to {message.author.name} completed.")

@bot.tree.command(name="ignore", description="[OWNER ONLY] Add a user to the ignore list.")
async def ignore_command(interaction: discord.Interaction, user_id: str, hours: int = None):
    if not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("Only the Owner is authorized to run this command.", ephemeral=True)
        return
        
    try:
        uid = int(user_id)
        ban_user(uid, duration_hours=hours)
        if hours:
            await interaction.response.send_message(f"User ID {uid} has been ignored for {hours} hours.", ephemeral=True)
        else:
            await interaction.response.send_message(f"User ID {uid} has been permanently ignored.", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("Invalid User ID.", ephemeral=True)

@bot.tree.command(name="unignore", description="[OWNER ONLY] Remove a user from the ignore list.")
async def unignore_command(interaction: discord.Interaction, user_id: str):
    if not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("Only the Owner is authorized to run this command.", ephemeral=True)
        return
        
    try:
        uid = int(user_id)
        if uid in banned_users:
            del banned_users[uid]
            save_blacklist(banned_users)
            await interaction.response.send_message(f"User ID {uid} has been removed from the ignore list.", ephemeral=True)
        else:
            await interaction.response.send_message(f"User ID {uid} is not on the ignore list.", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("Invalid User ID.", ephemeral=True)

@bot.tree.command(name="analyze", description="Run a deep analysis on a topic using the wiki or databases.")
async def analyze_command(interaction: discord.Interaction, query: str):
    global api_exhausted_until
    
    if time.time() < api_exhausted_until:
        await interaction.response.send_message("I am currently in a rest state due to API token exhaustion. Please try again in a minute.", ephemeral=True)
        return
    if is_banned(interaction.user.id):
        await interaction.response.send_message("You are not authorized to use this bot.", ephemeral=True)
        return
        
    if not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("Only the Owner is authorized to run heavy analysis slash commands to preserve API limits.", ephemeral=True)
        return
        
    guild_id = interaction.guild.id if interaction.guild else None
    if guild_id != TEST_SERVER_ID and (guild_id != CAPRICA_SERVER_ID or interaction.channel_id not in ALLOWED_CAPRICA_CHANNELS):
        await interaction.response.send_message("I am currently restricted.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    print(f"[{time.strftime('%X')}] Received /analyze command from {interaction.user.name}. Query: {query}")
    
    chat_history = f"System: The user invoked an explicit analysis slash command with query: {query}"
    
    is_test = (guild_id == TEST_SERVER_ID)
    current_user_context = f"{interaction.user.name} (ID: {interaction.user.id})"
    
    response = await generate_response(query, chat_history, is_test_server=is_test, current_user=current_user_context)
    
    # Check API Exhaustion
    if response == "<API_EXHAUSTED>":
        api_exhausted_until = time.time() + 60
        await interaction.followup.send("*(Ilse enters a state of rest. I have run out of API tokens and will ignore all requests for the next minute while my quota refreshes.)*")
        return
    
    if "<BLOCK_USER>" in response:
        if not is_owner_or_authorized(interaction.user):
            ban_user(interaction.user.id)
            await interaction.followup.send(f"I will not tolerate this conduct, {interaction.user.mention}.")
            return
        else:
            response = response.replace("<BLOCK_USER>", "")
            
    if "<STRIKE_USER>" in response:
        if not is_owner_or_authorized(interaction.user):
            user_behavior_strikes[interaction.user.id] = user_behavior_strikes.get(interaction.user.id, 0) + 1
            if user_behavior_strikes[interaction.user.id] >= 3:
                ban_user(interaction.user.id)
                await interaction.followup.send(f"You have been permanently banned for repeated infractions, {interaction.user.mention}.")
                return
            else:
                await interaction.followup.send(f"I will not tolerate slurs, inappropriate conduct, or flirting, {interaction.user.mention}. (Strike {user_behavior_strikes[interaction.user.id]}/3)")
                return
        else:
            response = response.replace("<STRIKE_USER>", "")
    
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
