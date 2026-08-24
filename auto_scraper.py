import discord
import asyncio
import sqlite3
import re
import subprocess
from datetime import datetime, timezone
import aiohttp

import export_json
import reorder_bills

CHANNEL_ID = 1189604125911044279
BOT_ID = 437618149505105920

async def check_and_update_bills(bot: discord.Client):
    print(f"[{datetime.now().strftime('%X')}] Starting automated bill check...")
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Auto-Scraper: Could not find bills channel.")
        return

    new_bills_added = False
    bills_to_insert = []
    # Get the last ~50 messages
    async for message in channel.history(limit=50):
        if message.author.id == BOT_ID and message.embeds:
            embed = message.embeds[0]
            desc = embed.description or ""
            
            # Extract Proposer
            proposer_name = "Unknown"
            if message.interaction:
                proposer_name = message.interaction.user.name
            elif "By" in desc:
                proposer_name = desc.split("By")[-1].split("\n")[0].strip()
                
            # Extract Doc Link
            doc_link = None
            match = re.search(r'https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)', desc)
            if match:
                doc_link = match.group(0)
                
            # Extract Title
            title = "Unknown Bill"
            title_match = re.search(r'\[(.*?)\]\(https://docs', desc)
            if title_match:
                title = title_match.group(1)
            else:
                lines = desc.split('\n')
                if len(lines) > 1:
                    title = lines[1].replace("Amend the ", "").replace("Pass the ", "").strip()
            
            date_str = message.created_at.strftime("%Y-%m-%d")

            # Check if bill already exists in DB
            conn = sqlite3.connect('memory.db', timeout=15)
            c = conn.cursor()
            c.execute("SELECT id FROM bills WHERE title = ?", (title,))
            exists = c.fetchone() is not None
            conn.close()

            if not exists:
                print(f"Auto-Scraper: Found new bill -> {title}")
                bills_to_insert.append((title, date_str, proposer_name, doc_link, "Pending analysis.", None))

    if bills_to_insert:
        conn = sqlite3.connect('memory.db', timeout=15)
        c = conn.cursor()
        c.executemany('''
            INSERT INTO bills (title, date, proposer, doc_link, main_goal, ilse_opinion)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', bills_to_insert)
        conn.commit()
        conn.close()
        new_bills_added = True

    # Update timestamp in system_status to reflect the successful check
    conn = sqlite3.connect('memory.db', timeout=15)
    c = conn.cursor()
    now = datetime.now(timezone.utc).timestamp()
    c.execute("UPDATE system_status SET last_update = ? WHERE id = 1", (now,))
    conn.commit()
    conn.close()

    if new_bills_added:
        print("Auto-Scraper: New bills added. Updating files and pushing to GitHub...")
        # 1. Update JSON
        export_json.export()
        # 2. Update MD
        reorder_bills.regenerate()
        try:
            subprocess.run(["git", "add", "bills.json", "bills.md", "status.json"], check=True)
            subprocess.run(["git", "commit", "-m", "Auto-update bills via Ilse Bot"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Auto-Scraper: Successfully pushed changes to GitHub.")
        except subprocess.CalledProcessError as e:
            print(f"Auto-Scraper: Git operation failed -> {e}")
    else:
        print("Auto-Scraper: No new bills found.")

REGIONAL_FORUM_ID = 1336732215266246739
GOV_CHANNEL_ID = 1336731816849178675

async def get_doc_title(doc_link):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(doc_link, timeout=5) as resp:
                html = await resp.text()
                match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                if match:
                    title = match.group(1).replace(" - Google Docs", "").strip()
                    return title
    except Exception as e:
        print(f"Error fetching title: {e}")
    return "Unknown Regional Bill"

async def check_regional_bills(bot: discord.Client):
    print(f"[{datetime.now().strftime('%X')}] Starting automated regional bill check...")
    forum = bot.get_channel(REGIONAL_FORUM_ID)
    if not forum or not isinstance(forum, discord.ForumChannel):
        print("Auto-Scraper: Could not find regional forum channel.")
        return

    threads = forum.threads
    for thread in threads:
        region_name = thread.name
        async for message in thread.history(limit=50):
            doc_link = None
            
            # Check for direct doc link
            match = re.search(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+', message.content)
            if match:
                doc_link = match.group(0)
            
            # Check for message link to gov channel
            else:
                msg_match = re.search(rf'https://discord\.com/channels/[0-9]+/{GOV_CHANNEL_ID}/([0-9]+)', message.content)
                if msg_match:
                    try:
                        msg_id = int(msg_match.group(1))
                        gov_channel = bot.get_channel(GOV_CHANNEL_ID)
                        if gov_channel:
                            gov_msg = await gov_channel.fetch_message(msg_id)
                            doc_match = re.search(r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+', gov_msg.content)
                            if doc_match:
                                doc_link = doc_match.group(0)
                    except Exception as e:
                        print(f"Failed to fetch governor message: {e}")
            
            if doc_link:
                # check if doc_link already in DB
                conn = sqlite3.connect('memory.db', timeout=15)
                c = conn.cursor()
                c.execute("SELECT id FROM regional_bills WHERE doc_link = ?", (doc_link,))
                exists = c.fetchone() is not None
                conn.close()

                if not exists:
                    print(f"Auto-Scraper: Found new regional bill in {region_name}")
                    title = await get_doc_title(doc_link)
                    date_str = message.created_at.strftime("%Y-%m-%d")
                    proposer_name = message.author.name
                    
                    conn = sqlite3.connect('memory.db', timeout=15)
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO regional_bills (title, region, date, proposer, doc_link)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (title, region_name, date_str, proposer_name, doc_link))
                    conn.commit()
                    conn.close()

LORE_CHANNELS = [
    1279459460074700875, # domestic events
    1213483620669333564, # responses to domestic events (has threads)
    1210983120866775050, # global events
    1308836707575267358, # election announcements
    1247442643177181245, # presidential announcements
    1199160589524676658, # government announcements
    1537208669631160370, # shadow government announcements
    1364234224630108390, # parliament announcements
    1336731816849178675, # governor announcements
    1222250149267640350, # court announcements
    1191519838837944400  # rulings
]

async def scrape_lore_channels(bot: discord.Client):
    print(f"[{datetime.now().strftime('%X')}] Starting automated lore channel backup...")
    lore_to_insert = []
    
    for channel_id in LORE_CHANNELS:
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
            
        # Process main channel messages
        if isinstance(channel, (discord.TextChannel, discord.ForumChannel, discord.Thread)):
            if isinstance(channel, discord.TextChannel):
                async for message in channel.history(limit=100):
                    # Skip empty messages (like images without text)
                    if not message.content.strip():
                        continue
                    lore_to_insert.append((str(message.id), channel.name, "Main", message.author.name, message.content, message.created_at.strftime("%Y-%m-%d %H:%M")))
            
            # Process active threads in the channel
            if hasattr(channel, 'threads'):
                for thread in channel.threads:
                    async for message in thread.history(limit=100):
                        if not message.content.strip():
                            continue
                        lore_to_insert.append((str(message.id), channel.name, thread.name, message.author.name, message.content, message.created_at.strftime("%Y-%m-%d %H:%M")))
                    
    if lore_to_insert:
        conn = sqlite3.connect('memory.db', timeout=15)
        c = conn.cursor()
        c.executemany('''
            INSERT OR IGNORE INTO discord_lore (message_id, channel_name, thread_name, author, content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', lore_to_insert)
        conn.commit()
        conn.close()
    
    print("Lore channel backup completed.")
