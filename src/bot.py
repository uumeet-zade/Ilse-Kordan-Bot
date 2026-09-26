import os
import re
import base64
import json
import io
from PIL import Image
import discord
import asyncio
from discord.ext import commands, tasks
import time
from dotenv import load_dotenv
from aiohttp import web
import subprocess

from brain import generate_response
import auto_scraper

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))
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
        self.generation_lock = asyncio.Lock()
        await self.tree.sync()
        print("Slash commands synced.")

bot = IlseBot()

TEST_SERVER_ID = 1537631696743174224
CAPRICA_SERVER_ID = 1189603606568108103
ALLOWED_CAPRICA_CHANNELS = [1266040682213281955, 1189630582280441997]

# --- Anti-Spam & Blacklist System ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLACKLIST_FILE = os.path.join(BASE_DIR, "data", "blacklist.json")
user_last_ping = {} # {user_id: timestamp}
user_think_cooldowns = {} # {user_id: timestamp}
user_spam_strikes = {}
latest_thoughts = {} # {user_id: thought}
global_latest_thought = {"user": None, "thought": None}
user_behavior_strikes = {} # {user_id: count}
COOLDOWN_SECONDS = 3
api_exhausted_until = 0
override_mode = False
last_say_channel = {}
active_websockets = set()
DMS_FILE = os.path.join(BASE_DIR, "data", "active_dms.json")

def load_dms():
    if os.path.exists(DMS_FILE):
        try:
            with open(DMS_FILE, "r") as f:
                return set(json.load(f))
        except:
            pass
    return set()

def save_dms():
    try:
        with open(DMS_FILE, "w") as f:
            json.dump(list(active_dms), f)
    except:
        pass

active_dms = load_dms()

def trigger_mac_notification(title, text):
    try:
        # Escape quotes to prevent injection
        safe_title = title.replace('"', '\\"')
        safe_text = text.replace('"', '\\"')
        apple_script = f'display notification "{safe_text}" with title "{safe_title}" sound name "Glass"'
        subprocess.run(["osascript", "-e", apple_script])
    except:
        pass

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
    if guild_id == CAPRICA_SERVER_ID:
        if message.channel.id == 1189630582280441997:
            if is_owner_or_authorized(message.author):
                return True
            return False
        if message.channel.id in ALLOWED_CAPRICA_CHANNELS:
            return True
    return False

async def extract_linked_messages(content: str, bot: discord.Client) -> str:
    link_pattern = r'https://discord\.com/channels/([0-9]+)/([0-9]+)/([0-9]+)'
    links = re.findall(link_pattern, content)
    if not links:
        return ""
        
    context = ""
    for guild_id_str, channel_id_str, message_id_str in links:
        guild_id = int(guild_id_str)
        channel_id = int(channel_id_str)
        message_id = int(message_id_str)
        
        if guild_id not in [CAPRICA_SERVER_ID, TEST_SERVER_ID]:
            continue
            
        try:
            channel = bot.get_channel(channel_id)
            if not channel:
                channel = await bot.fetch_channel(channel_id)
            if not channel:
                continue
                
            msg = await channel.fetch_message(message_id)
            
            verification_status = ""
            if channel_id == 1287587112912289833: # Caprik
                msg_lower = msg.content.lower()
                if '🔒' in msg.content or 'lock' in msg_lower:
                    verification_status = " [STATUS: UNVERIFIED/LOCKED (Treat as rumor/unofficial)]"
                elif 'verified' in msg_lower and '<:' in msg.content:
                    verification_status = " [STATUS: VERIFIED]"
                else:
                    verification_status = " [STATUS: UNVERIFIED (Treat as rumor/unofficial)]"
            
            context += f"Message by {msg.author.display_name} in #{channel.name}:\n\"{msg.content}\"\n{verification_status}\n\n"
        except Exception as e:
            print(f"Failed to fetch linked message {message_id}: {e}")
            
    return context.strip()

@tasks.loop(hours=2)
async def daily_bill_update():
    await auto_scraper.check_and_update_bills(bot)
    await auto_scraper.check_regional_bills(bot)
    await auto_scraper.scrape_lore_channels(bot)
    await auto_scraper.analyze_pending_bills(bot)

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

    if not hasattr(bot, 'web_server_started'):
        bot.web_server_started = True
        bot.loop.create_task(start_web_server())

@bot.event
async def on_message(message):
    global api_exhausted_until, override_mode

    if isinstance(message.channel, discord.DMChannel):
        if message.author.id not in active_dms:
            active_dms.add(message.author.id)
            save_dms()
        
        if message.author != bot.user:
            trigger_mac_notification(f"Ilse Kordan DM: {message.author.name}", message.content)

    # WebSocket Broadcast
    if active_websockets:
        import json
        ws_channel_id = str(message.channel.id)
        if isinstance(message.channel, discord.DMChannel):
            if getattr(message.channel, 'recipient', None):
                ws_channel_id = str(message.channel.recipient.id)
            elif message.author != bot.user:
                ws_channel_id = str(message.author.id)
                
        msg_data = {
            "type": "MESSAGE_CREATE",
            "channel_id": ws_channel_id,
            "is_dm": isinstance(message.channel, discord.DMChannel),
            "is_bot": message.author == bot.user,
            "message": {
                "author_name": message.author.display_name,
                "author_avatar": message.author.display_avatar.url if message.author.display_avatar else "",
                "content": message.content,
                "timestamp": message.created_at.isoformat()
            }
        }
        for ws in list(active_websockets):
            try:
                bot.loop.create_task(ws.send_str(json.dumps(msg_data)))
            except:
                pass

    if message.author == bot.user:
        return

    # Manual Override Command
    if message.content == "!override" and is_owner_or_authorized(message.author):
        override_mode = not override_mode
        await message.reply(f"*(OOC: Override mode is now **{'ON' if override_mode else 'OFF'}**. I will {'ignore all prompts' if override_mode else 'resume normal operation'}.)*")
        return

    # Manual Say Command (Format: !say <channel_id> <message> OR !say <message>)
    if message.content.startswith("!say ") and is_owner_or_authorized(message.author):
        parts = message.content.split(" ", 2)
        target_channel_id = None
        text_to_send = ""
        
        if len(parts) >= 2:
            if parts[1].isdigit():
                target_channel_id = int(parts[1])
                text_to_send = parts[2] if len(parts) > 2 else ""
            else:
                text_to_send = message.content[5:]
                
        if not target_channel_id:
            last_data = last_say_channel.get(message.author.id)
            if last_data and time.time() - last_data["timestamp"] < 300: # 5 minutes
                target_channel_id = last_data["channel_id"]
            else:
                await message.reply("No recent channel specified or time limit (5m) expired. Use `!say <channel_id> <message>`.")
                return

        if target_channel_id and text_to_send:
            try:
                target = bot.get_channel(target_channel_id)
                if not target:
                    try:
                        target = await bot.fetch_user(target_channel_id)
                    except:
                        target = None

                if target:
                    await target.send(text_to_send)
                    await message.add_reaction("✅")
                    last_say_channel[message.author.id] = {"channel_id": target_channel_id, "timestamp": time.time()}
                else:
                    await message.reply("Channel or User not found.")
            except Exception as e:
                await message.reply(f"Error: {e}")
        else:
            await message.reply("Format: `!say <channel_id> <message>` or `!say <message>` (if channel was recently used).")
        return

    # If override is active, ignore all normal messages
    if override_mode:
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

        print(f"[{time.strftime('%X')}] Received mention from {message.author.display_name}. Generating response...")
        await message.add_reaction("⏳")
        
        async with bot.generation_lock:
            async with message.channel.typing():
                chat_history = ""
                async for msg in message.channel.history(limit=15, before=message):
                    chat_history = f"{msg.author.display_name} (Username: {msg.author.name}, ID: {msg.author.id}): {msg.content}\n" + chat_history
                
                # Fetch referenced message if replying to someone
                if message.reference and message.reference.message_id:
                    try:
                        ref_msg = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                        chat_history = f"[CONTEXT - PINGER REPLIED TO THIS MESSAGE]\n{ref_msg.author.display_name} (Username: {ref_msg.author.name}, ID: {ref_msg.author.id}): {ref_msg.content}\n[END CONTEXT]\n\n" + chat_history
                    except Exception as e:
                        print(f"Failed to fetch referenced message: {e}")
                        
                # Check for image attachments
                image_data = None
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                img_bytes = await attachment.read()
                                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                                image_data = f"data:{attachment.content_type};base64,{base64_image}"
                                break
                            except Exception as e:
                                print(f"Failed to read image: {e}")
                
                is_test = (message.guild.id == TEST_SERVER_ID) if message.guild else False
                current_user_context = f"{message.author.display_name} (Username: {message.author.name}, ID: {message.author.id})"
                
                linked_context = await extract_linked_messages(message.content, bot)
                
                response = await generate_response(message.content, chat_history, is_test_server=is_test, current_user=current_user_context, image_data=image_data, linked_messages_context=linked_context, discord_bot=bot, is_general_chat=(message.channel.id == 1189630582280441997))
                
                # Extract and log internal thoughts (allow for misspelled or missing closing tags)
                thoughts = re.findall(r'<THOUGHT>(.*?)(?:</[a-zA-Z]+>|$)', response, re.DOTALL | re.IGNORECASE)
                combined_thought = ""
                for thought in thoughts:
                    combined_thought += thought.strip() + "\n"
                    with open("thoughts.log", "a") as f:
                        f.write(f"[{time.strftime('%X')}] Response to {message.author.display_name}:\n{thought.strip()}\n\n")
                
                
                if combined_thought:
                    latest_thoughts[message.author.id] = combined_thought.strip()
                    global_latest_thought["user"] = message.author.display_name
                    global_latest_thought["thought"] = combined_thought.strip()
                
                # Strip thoughts from the actual response sent to Discord
                response = re.sub(r'<THOUGHT>.*?(?:</[a-zA-Z]+>|$)', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
                
                # Forcefully remove larpy sign-offs that the LLM stubbornly generates
                response = re.sub(r'(?i)(?:Now,?\s*)?if you\'?ll excuse me.*', '', response, flags=re.DOTALL).strip()
                
                try:
                    await message.remove_reaction("⏳", bot.user)
                except:
                    pass
                
                # Check API Exhaustion
                if response == "<API_EXHAUSTED>":
                    api_exhausted_until = time.time() + 60
                    await message.reply("*(Ilse enters a state of rest. I have run out of API tokens and will ignore all requests for the next minute while my quota refreshes.)*")
                    return
    
                if "<IGNORE>" in response:
                    return
                    
                # Check for AI-driven Ban
                if "<BLOCK_USER>" in response:
                    if not is_owner_or_authorized(message.author):
                        ban_user(message.author.id)
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
                            await message.channel.send(f"You have been permanently banned for repeated infractions, {message.author.mention}.")
                            return
                        else:
                            await message.channel.send(f"I will not tolerate slurs, inappropriate conduct, or flirting, {message.author.mention}. (Strike {user_behavior_strikes[message.author.id]}/3)")
                            return
                    else:
                        response = response.replace("<STRIKE_USER>", "")
                
                # Chunk response if > 2000 chars
                if len(response) > 2000:
                    await message.reply(response[:1900])
                    for chunk in [response[i:i+1900] for i in range(1900, len(response), 1900)]:
                        await message.channel.send(chunk)
                else:
                    await message.reply(response)
            
        print(f"[{time.strftime('%X')}] Response to {message.author.name} completed.")

@bot.tree.command(name="thoughts", description="[OWNER ONLY] Read Ilse's internal thoughts from her last response to a user.")
async def thoughts_command(interaction: discord.Interaction, user: discord.User = None):
    if not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("Only the Owner is authorized to run this command.", ephemeral=True)
        return
        
    if user:
        target_name = user.name
        thought = latest_thoughts.get(user.id)
    else:
        target_name = global_latest_thought.get("user")
        thought = global_latest_thought.get("thought")
        
    if not thought:
        await interaction.response.send_message(f"No recent thoughts recorded.", ephemeral=True)
        return
        
    embed = discord.Embed(title=f"Ilse's Thoughts regarding {target_name}", description=thought[:4090], color=discord.Color.dark_grey())
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
    if is_banned(interaction.user.id):
        await interaction.response.send_message("You are not authorized to use this bot.", ephemeral=True)
        return

    guild_id = interaction.guild.id if interaction.guild else None
    if guild_id != TEST_SERVER_ID and (guild_id != CAPRICA_SERVER_ID or interaction.channel_id not in ALLOWED_CAPRICA_CHANNELS):
        await interaction.response.send_message("I am currently restricted from this channel.", ephemeral=True)
        return

    # Add general channel check
    if guild_id == CAPRICA_SERVER_ID and interaction.channel_id == 1189630582280441997 and not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("I only respond to my owner in this channel.", ephemeral=True)
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
    
    response = await generate_response(query, chat_history, is_test_server=is_test, current_user=current_user_context, force_model="glm-5-2")
    
    # Check API Exhaustion
    if response == "<API_EXHAUSTED>":
        api_exhausted_until = time.time() + 60
        await interaction.followup.send("*(Ilse enters a state of rest. I have run out of API tokens and will ignore all requests for the next minute while my quota refreshes.)*")
        return
        
    # Extract and log internal thoughts (allow for misspelled or missing closing tags)
    thoughts = re.findall(r'<THOUGHT>(.*?)(?:</[a-zA-Z]+>|$)', response, re.DOTALL | re.IGNORECASE)
    combined_thought = ""
    for thought in thoughts:
        combined_thought += thought.strip() + "\n"
        with open("thoughts.log", "a") as f:
            f.write(f"[{time.strftime('%X')}] /analyze Response to {interaction.user.display_name}:\n{thought.strip()}\n\n")
            
    if combined_thought:
        latest_thoughts[interaction.user.id] = combined_thought.strip()
        global_latest_thought["user"] = interaction.user.display_name
        global_latest_thought["thought"] = combined_thought.strip()
        
    # Strip thoughts from the actual response sent to Discord
    response = re.sub(r'<THOUGHT>.*?(?:</[a-zA-Z]+>|$)', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
    
    # Forcefully remove larpy sign-offs
    response = re.sub(r'(?i)(?:Now,?\s*)?if you\'?ll excuse me.*', '', response, flags=re.DOTALL).strip()
    
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

@bot.tree.command(name="think", description="Run a deep analysis query using the flagship GLM-5-2 model.")
async def think_command(interaction: discord.Interaction, query: str):
    if is_banned(interaction.user.id):
        await interaction.response.send_message("You are not authorized to use this bot.", ephemeral=True)
        return
        
    guild_id = interaction.guild.id if interaction.guild else None
    if guild_id != TEST_SERVER_ID and (guild_id != CAPRICA_SERVER_ID or interaction.channel_id not in ALLOWED_CAPRICA_CHANNELS):
        await interaction.response.send_message("I am currently restricted from this channel.", ephemeral=True)
        return

    # Add general channel check
    if guild_id == CAPRICA_SERVER_ID and interaction.channel_id == 1189630582280441997 and not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("I only respond to my owner in this channel.", ephemeral=True)
        return
        
    guild_id = interaction.guild.id if interaction.guild else None
    if guild_id != TEST_SERVER_ID and (guild_id != CAPRICA_SERVER_ID or interaction.channel_id not in ALLOWED_CAPRICA_CHANNELS):
        await interaction.response.send_message("I am currently restricted from this channel.", ephemeral=True)
        return

    if not is_owner_or_authorized(interaction.user):
        now = time.time()
        last_used = user_think_cooldowns.get(interaction.user.id, 0)
        if now - last_used < 180:
            remaining = int(180 - (now - last_used))
            await interaction.response.send_message(f"Please wait {remaining} seconds before using this command again.", ephemeral=True)
            return
        user_think_cooldowns[interaction.user.id] = now

    await interaction.response.defer()
    
    try:
        print(f"[{time.strftime('%X')}] Received /think from {interaction.user.display_name}. Forcing glm-5-2.")
        
        chat_history = ""
        async for msg in interaction.channel.history(limit=15):
            chat_history = f"{msg.author.display_name} (Username: {msg.author.name}, ID: {msg.author.id}): {msg.content}\n" + chat_history
            
        is_test = (interaction.guild.id == TEST_SERVER_ID) if interaction.guild else False
        current_user_context = f"{interaction.user.display_name} (Username: {interaction.user.name}, ID: {interaction.user.id})"
        
        linked_context = await extract_linked_messages(query, bot)
        
        response = await generate_response(query, chat_history, is_test_server=is_test, current_user=current_user_context, image_data=None, force_model="glm-5-2", linked_messages_context=linked_context, discord_bot=bot, is_general_chat=(interaction.channel_id == 1189630582280441997))
        
        if response == "<API_EXHAUSTED>":
            global api_exhausted_until
            api_exhausted_until = time.time() + 60
            await interaction.followup.send("*(Ilse enters a state of rest. I have run out of API tokens and will ignore all requests for the next minute while my quota refreshes.)*")
            return
            
        thoughts = re.findall(r'<THOUGHT>(.*?)(?:</[a-zA-Z]+>|$)', response, re.DOTALL | re.IGNORECASE)
        combined_thought = ""
        for thought in thoughts:
            combined_thought += thought.strip() + "\n"
            with open("thoughts.log", "a") as f:
                f.write(f"[{time.strftime('%X')}] Response to {interaction.user.display_name}:\n{thought.strip()}\n\n")
                
        if combined_thought:
            latest_thoughts[interaction.user.id] = combined_thought.strip()
            global_latest_thought["user"] = interaction.user.display_name
            global_latest_thought["thought"] = combined_thought.strip()
            
        response = re.sub(r'<THOUGHT>.*?(?:</[a-zA-Z]+>|$)', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
        
        # Forcefully remove larpy sign-offs
        response = re.sub(r'(?i)(?:Now,?\s*)?if you\'?ll excuse me.*', '', response, flags=re.DOTALL).strip()
        
        # Check security tags
        if "<BLOCK_USER>" in response:
            ban_user(interaction.user.id)
            await interaction.followup.send(f"You have been permanently blocked for security reasons, {interaction.user.mention}.")
            return
            
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
            
        print(f"[{time.strftime('%X')}] /think response to {interaction.user.name} completed.")
    except Exception as e:
        print(f"Error in /think command: {e}")
        try:
            await interaction.followup.send(f"An internal error occurred: {e}", ephemeral=True)
        except:
            pass

@bot.tree.command(name="analyze_pending_bills", description="[OWNER ONLY] Manually trigger analysis of all bills with pending analysis.")
async def analyze_pending_command(interaction: discord.Interaction):
    if not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("Only the Owner is authorized to run this command.", ephemeral=True)
        return
    
    await interaction.response.defer(thinking=True, ephemeral=True)
    print(f"[{time.strftime('%X')}] Manual pending bills analysis triggered by {interaction.user.name}")
    
    try:
        await auto_scraper.analyze_pending_bills(bot)
        await interaction.followup.send("Pending bills analysis completed successfully.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error during analysis: {str(e)}", ephemeral=True)
        print(f"Error in manual pending bills analysis: {e}")

# --- WEB DASHBOARD INTEGRATION ---
async def api_channels(request):
    guilds_data = []
    for guild in bot.guilds:
        channels_data = []
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).read_messages:
                channels_data.append({"id": str(channel.id), "name": channel.name})
        guilds_data.append({"id": str(guild.id), "name": guild.name, "channels": channels_data})
    
    dms_data = []
    for user_id in active_dms:
        try:
            user = bot.get_user(user_id) or await bot.fetch_user(user_id)
            if user:
                dms_data.append({"id": str(user.id), "name": user.name})
        except:
            pass
            
    return web.json_response({"guilds": guilds_data, "dms": dms_data})

async def api_messages(request):
    channel_id = request.query.get('channel_id')
    if not channel_id:
        return web.json_response([], status=400)
    
    target = bot.get_channel(int(channel_id))
    if not target:
        try:
            user = bot.get_user(int(channel_id)) or await bot.fetch_user(int(channel_id))
            if user:
                target = user.dm_channel or await user.create_dm()
        except:
            pass
    
    if not target:
        return web.json_response([], status=404)
        
    messages_data = []
    try:
        async for msg in target.history(limit=50):
            messages_data.append({
                "author_name": msg.author.display_name,
                "author_avatar": msg.author.display_avatar.url if msg.author.display_avatar else "",
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            })
    except Exception as e:
        print(f"Error fetching history: {e}")
        
    return web.json_response(messages_data)

async def api_send(request):
    data = await request.json()
    channel_id = data.get('channel_id')
    content = data.get('content')
    if not channel_id or not content:
        return web.json_response({"error": "Missing data"}, status=400)
        
    target = bot.get_channel(int(channel_id))
    if not target:
        try:
            user = bot.get_user(int(channel_id)) or await bot.fetch_user(int(channel_id))
            if user:
                target = user.dm_channel or await user.create_dm()
                if user.id not in active_dms:
                    active_dms.add(user.id)
                    save_dms()
        except:
            pass
            
    if target:
        try:
            await target.send(content)
            return web.json_response({"status": "sent"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    return web.json_response({"error": "Channel not found"}, status=404)

async def serve_dashboard(request):
    try:
        dash_path = os.path.join(BASE_DIR, "web", "dashboard.html")
        with open(dash_path, "r") as f:
            return web.Response(text=f.read(), content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="dashboard.html not found", status=404)

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    active_websockets.add(ws)
    try:
        async for msg in ws:
            pass
    finally:
        active_websockets.discard(ws)
    return ws

async def api_new_dm(request):
    data = await request.json()
    user_id = data.get('user_id')
    if not user_id:
        return web.json_response({"error": "Missing user_id"}, status=400)
    
    try:
        user = bot.get_user(int(user_id)) or await bot.fetch_user(int(user_id))
        if user:
            if user.id not in active_dms:
                active_dms.add(user.id)
                save_dms()
            return web.json_response({"status": "success", "id": str(user.id), "name": user.name})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
    return web.json_response({"error": "User not found"}, status=404)

@bot.tree.command(name="shutdown", description="[OWNER ONLY] Shut down the bot completely.")
async def shutdown_command(interaction: discord.Interaction):
    if not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("You do not have permission to shut me down.", ephemeral=True)
        return
        
    await interaction.response.send_message("Shutting down... Goodbye!")
    print(f"[INFO] Shutdown command received from {interaction.user.name}.")
    import sys
    await bot.close()
    sys.exit(0)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', serve_dashboard)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/api/channels', api_channels)
    app.router.add_get('/api/messages', api_messages)
    app.router.add_post('/api/send', api_send)
    app.router.add_post('/api/dms/new', api_new_dm)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 5050)
    try:
        await site.start()
        print("[INFO] Web Dashboard started on http://localhost:5050")
    except OSError as e:
        print(f"[ERROR] Could not start Web Dashboard on port 5050: {e}")

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN is not set in .env")
    else:
        bot.run(TOKEN)
