import discord
import asyncio
import sqlite3
import re
import subprocess
from datetime import datetime, timezone
import aiohttp
import urllib.request
import os
import json
from mistralai import Mistral
from dotenv import load_dotenv

import export_json
import reorder_bills

load_dotenv()
mistral_client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

PROMPT = """
You are Ilse Kordan, a Social Democrat and Ordoliberal politician in Caprica. 
You are analyzing a proposed legislative bill.

Output your response strictly as a JSON object matching this exact schema:
{
  "main_goal": "A 1-2 sentence objective summary of what this bill seeks to accomplish.",
  "ilse_liked": "What you (as Ilse) LIKE about this bill based on your Ordoliberal/working-class ideology. (If nothing, say 'Nothing').",
  "ilse_disliked": "What you (as Ilse) DISLIKE about this bill. (If nothing, say 'Nothing').",
  "category": "Must be exactly one of: Economy, Infrastructure, Public Health, Security & Justice, Foreign Policy, Government & Nominations, Social Policy, Misc."
}

Bill Content:
"""

CHANNEL_ID = 1189604125911044279
BOT_ID = 437618149505105920


def read_google_doc_sync(url: str) -> str:
    """Synchronous version of read_google_doc to extract text from a Google Doc."""
    import re
    try:
        match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', url)
        if not match:
            return ""
        doc_id = match.group(1)
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        req = urllib.request.Request(export_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            text = response.read().decode('utf-8')
            text = re.sub(r'^\s*Page\s*$', '', text, flags=re.MULTILINE)
            text = re.sub(r'_{10,}', '', text)
            return text.strip()
    except Exception as e:
        print(f"Error reading Google Doc {url}: {e}")
        return ""


def extract_main_goal_llm(text: str, title: str):
    """Extract main goal, opinion, and category from bill text using Mistral."""
    if not text or not text.strip():
        return "Pending analysis.", None, "Misc."
        
    try:
        messages = [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Title: {title}\n\n{text[:8000]}"}
        ]
        
        response = mistral_client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        opinion_text = f"**What Ilse Liked:** {data.get('ilse_liked', 'Nothing')}\n\n**What Ilse Disliked:** {data.get('ilse_disliked', 'Nothing')}"
        category = data.get('category', 'Misc.')
        
        valid_categories = ["Economy", "Infrastructure", "Public Health", "Security & Justice", "Foreign Policy", "Government & Nominations", "Social Policy", "Misc."]
        if category not in valid_categories:
            category = "Misc."
            
        return data.get('main_goal', title), opinion_text, category
    except Exception as e:
        print(f"Error during Mistral analysis for {title}: {e}")
        return title, None, "Misc."

def get_current_mp_count() -> int:
    try:
        conn = sqlite3.connect('memory.db', timeout=15)
        c = conn.cursor()
        def _count(header):
            c.execute("SELECT content FROM discord_lore WHERE channel_name LIKE '%election-announcements%' AND content LIKE ? ORDER BY timestamp DESC LIMIT 1", (f'%{header}%',))
            row = c.fetchone()
            if not row: return 0
            text = row[0]
            text = text.split('## Elected President')[0]
            text = text.split('## Elected Governor')[0]
            mentions = re.findall(r'<@([0-9]+)>', text)
            return len(set(mentions))
            
        total = _count('Elected Members of Parliament (regional)') + _count('Elected Members of Parliament (list)')
        conn.close()
        return total
    except Exception as e:
        print(f"Error getting MP count: {e}")
        return 0

async def check_and_update_bills(bot: discord.Client):
    print(f"[{datetime.now().strftime('%X')}] Starting automated bill check...")
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Auto-Scraper: Could not find bills channel.")
        return

    new_bills_added = False
    bills_to_insert = []
    bills_to_update_llm = []
    bills_to_update_votes = []
    
    total_mps = get_current_mp_count()
    print(f"Auto-Scraper: Current Parliament Size is {total_mps} MPs.")
    
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

            # Extract Votes
            votes_yay = None
            votes_nay = None
            votes_abstain = None
            votes_absent = None
            
            if "**Final Result**" in desc:
                yay_match = re.search(r'✅.*?\|\s*[\d.]+%?\s*\(([\d]+)\)', desc)
                abstain_match = re.search(r'🟨.*?\|\s*[\d.]+%?\s*\(([\d]+)\)', desc)
                nay_match = re.search(r'<:x_square:.*?>.*?\|\s*[\d.]+%?\s*\(([\d]+)\)', desc)
                if not nay_match:
                    nay_match = re.search(r'❌.*?\|\s*[\d.]+%?\s*\(([\d]+)\)', desc)
                
                if yay_match: votes_yay = int(yay_match.group(1))
                if nay_match: votes_nay = int(nay_match.group(1))
                if abstain_match: votes_abstain = int(abstain_match.group(1))
                
                if votes_yay is not None and votes_nay is not None and votes_abstain is not None:
                    if total_mps > 0:
                        votes_absent = max(0, total_mps - (votes_yay + votes_nay + votes_abstain))

            # Check if bill already exists in DB
            conn = sqlite3.connect('memory.db', timeout=15)
            c = conn.cursor()
            c.execute("SELECT id, doc_link, main_goal, votes_yay FROM bills WHERE title = ?", (title,))
            existing = c.fetchone()
            conn.close()

            if existing:
                bill_id, existing_doc_link, existing_main_goal, existing_votes = existing
                
                needs_llm = (existing_main_goal == "Pending analysis." and (doc_link or existing_doc_link))
                needs_votes = (existing_votes is None and votes_yay is not None)
                
                if needs_llm:
                    bills_to_update_llm.append((bill_id, title, doc_link or existing_doc_link, proposer_name, date_str, votes_yay, votes_nay, votes_abstain, votes_absent))
                elif needs_votes:
                    bills_to_update_votes.append((bill_id, votes_yay, votes_nay, votes_abstain, votes_absent))
                    
            elif not existing:
                print(f"Auto-Scraper: Found new bill -> {title}")
                main_goal = "Pending analysis."
                ilse_opinion = None
                category = "Misc."
                if doc_link:
                    doc_text = read_google_doc_sync(doc_link)
                    if doc_text:
                        main_goal, ilse_opinion, category = extract_main_goal_llm(doc_text, title)
                        print(f"Auto-Scraper: Extracted main goal: {main_goal[:80]}...")
                    else:
                        print(f"Auto-Scraper: Could not read Google Doc for {title}")
                bills_to_insert.append((title, date_str, proposer_name, doc_link, main_goal, ilse_opinion, votes_yay, votes_nay, votes_abstain, votes_absent, category))

    if bills_to_insert:
        conn = sqlite3.connect('memory.db', timeout=15)
        c = conn.cursor()
        c.executemany('''
            INSERT INTO bills (title, date, proposer, doc_link, main_goal, ilse_opinion, votes_yay, votes_nay, votes_abstain, votes_absent, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', bills_to_insert)
        conn.commit()
        conn.close()
        new_bills_added = True
    
    # Process bills that need analysis
    if bills_to_update_llm:
        print(f"Auto-Scraper: Found {len(bills_to_update_llm)} existing bills needing analysis...")
        conn = sqlite3.connect('memory.db', timeout=15)
        c = conn.cursor()
        for bill_id, title, doc_link, proposer, date_str, vy, vn, vab, vabsent in bills_to_update_llm:
            doc_text = read_google_doc_sync(doc_link)
            if doc_text:
                main_goal, ilse_opinion, category = extract_main_goal_llm(doc_text, title)
                print(f"Auto-Scraper: Updating bill {bill_id} ({title[:40]}...) with goal: {main_goal[:60]}...")
                c.execute("UPDATE bills SET main_goal = ?, ilse_opinion = ?, votes_yay = ?, votes_nay = ?, votes_abstain = ?, votes_absent = ?, category = ? WHERE id = ?", (main_goal, ilse_opinion, vy, vn, vab, vabsent, category, bill_id))
            else:
                print(f"Auto-Scraper: Could not read doc for existing bill {bill_id}")
        conn.commit()
        conn.close()
        new_bills_added = True

    # Process bills that only need votes updated
    if bills_to_update_votes:
        print(f"Auto-Scraper: Found {len(bills_to_update_votes)} existing bills needing votes updated...")
        conn = sqlite3.connect('memory.db', timeout=15)
        c = conn.cursor()
        for bill_id, vy, vn, vab, vabsent in bills_to_update_votes:
            c.execute("UPDATE bills SET votes_yay = ?, votes_nay = ?, votes_abstain = ?, votes_absent = ? WHERE id = ?", (vy, vn, vab, vabsent, bill_id))
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
        print("Auto-Scraper: Bills updated. Updating files and pushing to GitHub...")
        # 1. Update JSON
        export_json.export()
        # 2. Update MD
        reorder_bills.regenerate()
        try:
            subprocess.run(["git", "add", "bills.json", "status.json"], check=True)
            subprocess.run(["git", "commit", "-m", "Auto-update bills via Ilse Bot"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Auto-Scraper: Successfully pushed changes to GitHub.")
        except subprocess.CalledProcessError as e:
            print(f"Auto-Scraper: Git operation failed -> {e}")
    else:
        print("Auto-Scraper: No new bills found.")


async def analyze_pending_bills(bot: discord.Client):
    """One-time function to analyze ALL existing bills with 'Pending analysis.' main_goal."""
    print(f"[{datetime.now().strftime('%X')}] Starting one-time analysis of ALL pending bills...")
    
    conn = sqlite3.connect('memory.db', timeout=15)
    c = conn.cursor()
    c.execute("SELECT id, title, doc_link FROM bills WHERE main_goal = 'Pending analysis.' AND doc_link IS NOT NULL")
    pending_bills = c.fetchall()
    conn.close()
    
    if not pending_bills:
        print("No pending bills to analyze.")
        return
    
    print(f"Found {len(pending_bills)} bills with 'Pending analysis.' - starting analysis...")
    
    updated_count = 0
    conn = sqlite3.connect('memory.db', timeout=15)
    c = conn.cursor()
    
    for bill_id, title, doc_link in pending_bills:
        doc_text = read_google_doc_sync(doc_link)
        if doc_text:
            main_goal, ilse_opinion, category = extract_main_goal_llm(doc_text, title)
            c.execute("UPDATE bills SET main_goal = ?, ilse_opinion = ?, category = ? WHERE id = ?", (main_goal, ilse_opinion, category, bill_id))
            print(f"  Updated bill {bill_id} ({title[:50]}...) -> {main_goal[:70]}...")
            updated_count += 1
        else:
            print(f"  Could not read doc for bill {bill_id}: {title}")
    
    conn.commit()
    conn.close()
    
    print(f"Completed. Updated {updated_count}/{len(pending_bills)} bills.")
    
    # Regenerate output files
    export_json.export()
    reorder_bills.regenerate()
    
    try:
        subprocess.run(["git", "add", "bills.json", "status.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Analyzed all pending bills via Ilse Bot"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Successfully pushed changes to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed -> {e}")

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
