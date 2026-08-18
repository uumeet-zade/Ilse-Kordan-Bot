import os
import discord
from discord.ext import commands, tasks
import asyncio
import subprocess
from collections import defaultdict
import time
from dotenv import load_dotenv

from brain import generate_response
from database import get_connection

load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")

# Setup intent
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Anti-Spam & Rate Limiting
USER_COOLDOWN = 30 # seconds
user_last_ping = defaultdict(float)
request_queue = asyncio.Queue()

# Server and Channel Configurations
TEST_SERVER_ID = 1537631696743174224
CAPRICA_SERVER_ID = 1189603606568108103

CAPRICA_SPEAK_CHANNELS = [1266040682213281955]
CAPRICA_READ_CHANNELS = [
    1266040682213281955, # Also read from where she speaks
    1279459460074700875, 1213483620669333564, 1210983120866775050,
    1308836707575267358, 1247442643177181245, 1199160589524676658,
    1537208669631160370, 1364234224630108390, 1189604125911044279,
    1336731816849178675, 1337884164933947523, 1498948178463035464,
    1191519838837944400, 1222250149267640350
]

async def process_queue():
    """Background task to process one LLM request at a time."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        message, chat_history, is_test_server = await request_queue.get()
        try:
            # Generate response from dual-model router
            response = await generate_response(message.content, chat_history, is_test_server)
            
            # Keep responses under discord's 2000 char limit
            if len(response) > 2000:
                response = response[:1997] + "..."
                
            await message.channel.send(response)
        except Exception as e:
            print(f"Error processing message from queue: {e}")
            await message.channel.send("I encountered an error processing that request.")
        finally:
            request_queue.task_done()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    bot.loop.create_task(process_queue())
    daily_bill_scrape.start()
    bot_heartbeat.start()
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    guild_id = message.guild.id if message.guild else None
    channel_id = message.channel.id
    parent_id = getattr(message.channel, 'parent_id', None)

    can_read = False
    can_speak = False

    if guild_id == TEST_SERVER_ID:
        can_read = True
        can_speak = True
    elif guild_id == CAPRICA_SERVER_ID:
        if channel_id in CAPRICA_READ_CHANNELS or parent_id in CAPRICA_READ_CHANNELS:
            can_read = True
        if channel_id in CAPRICA_SPEAK_CHANNELS or parent_id in CAPRICA_SPEAK_CHANNELS:
            can_speak = True
    else:
        # Ignore other random servers she might be invited to
        return

    if not can_read and not can_speak:
        return

    if can_read:
        # Log context to buffer
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO discord_context (channel_id, author, content) VALUES (?, ?, ?)",
                  (str(message.channel.id), message.author.name, message.content))
        
        # Keep context buffer small (last 500 messages globally)
        c.execute("DELETE FROM discord_context WHERE id NOT IN (SELECT id FROM discord_context ORDER BY id DESC LIMIT 500)")
        conn.commit()
        conn.close()

    # Check if she should speak
    mentioned = bot.user in message.mentions
    if not mentioned:
        return
        
    if not can_speak:
        print(f"Ignored ping from {message.author.name}: Not permitted to speak in channel {channel_id}.")
        return

    # Check Cooldown
    now = time.time()
    if now - user_last_ping[message.author.id] < USER_COOLDOWN:
        await message.channel.send(f"Please wait {USER_COOLDOWN} seconds between requests, {message.author.name}.")
        return
        
    user_last_ping[message.author.id] = now
    
    # Fetch recent chat history for context
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT author, content FROM discord_context WHERE channel_id = ? ORDER BY id DESC LIMIT 10", (str(message.channel.id),))
    recent_msgs = c.fetchall()
    conn.close()
    
    chat_history = ""
    for r in reversed(recent_msgs):
        chat_history += f"{r[0]}: {r[1]}\n"

    # Queue the request instead of processing it immediately
    is_test_server = (guild_id == TEST_SERVER_ID)
    await request_queue.put((message, chat_history, is_test_server))

@tasks.loop(hours=24)
async def daily_bill_scrape():
    """Runs the study_bills.sh script once every 24 hours."""
    print("Starting automated daily bill scraping...")
    try:
        # Run the shell script asynchronously to not block the bot
        process = await asyncio.create_subprocess_shell(
            './study_bills.sh',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            print("Daily bill scrape completed successfully.")
            # Record the update timestamp
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute('UPDATE system_status SET last_update = ? WHERE id = 1', (time.time(),))
                conn.commit()
                conn.close()
                
                # Push the updated JSON files to git to trigger GitHub Pages
                print("Committing and pushing updated JSON to GitHub...")
                
                github_token = os.environ.get("GITHUB_TOKEN")
                
                if github_token:
                    push_cmd = f'git push https://uumeet-zade:{github_token}@github.com/uumeet-zade/Ilse-Kordan-Bot.git'
                else:
                    push_cmd = 'git push'
                    
                git_proc = await asyncio.create_subprocess_shell(
                    f'git add bills.json status.json && git commit -m "Automated daily bills update" && {push_cmd}',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                git_stdout, git_stderr = await git_proc.communicate()
                if git_proc.returncode == 0:
                    print("Successfully pushed to GitHub.")
                else:
                    print(f"Git push failed: {git_stderr.decode()}")
                    
            except Exception as e:
                print(f"Failed to record update time or push: {e}")
        else:
            print(f"Daily bill scrape failed: {stderr.decode()}")
    except Exception as e:
        print(f"Exception during daily bill scrape: {e}")

@tasks.loop(seconds=60)
async def bot_heartbeat():
    """Updates the heartbeat timestamp so the website knows the bot is online."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('UPDATE system_status SET last_heartbeat = ? WHERE id = 1', (time.time(),))
        conn.commit()
        conn.close()
    except Exception:
        pass

# Slash Commands
@bot.tree.command(name="ilse-update-roster", description="Update the Current State Ledger (Brain A)")
async def update_roster(interaction: discord.Interaction, name: str, status: str, faction: str, role: str, notes: str):
    # In a real bot, we'd add permission checks here (e.g., has_role("Admin"))
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO current_roster (character_name, status, faction, role, notes) 
                     VALUES (?, ?, ?, ?, ?)''', (name, status, faction, role, notes))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Ledger updated: {name} is now {status} as {role} of {faction}.")
    except Exception as e:
        await interaction.response.send_message(f"Error updating ledger: {e}", ephemeral=True)

@bot.tree.command(name="ilse-remove-roster", description="Remove a character from the Current State Ledger")
async def remove_roster(interaction: discord.Interaction, name: str):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM current_roster WHERE character_name = ?', (name,))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Removed {name} from the ledger.")
    except Exception as e:
        await interaction.response.send_message(f"Error removing from ledger: {e}", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not found in .env file.")
    else:
        bot.run(TOKEN)
