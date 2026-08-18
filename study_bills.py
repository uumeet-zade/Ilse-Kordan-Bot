import discord
import asyncio
import sqlite3
from database import get_connection
from export_json import export
import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = 1189604125911044279
BOT_ID = 437618149505105920
BILL_LIMIT = 20 # Limit to the 20 most recent bills

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    'gemini-3.1-flash-lite',
    generation_config={"response_mime_type": "application/json"}
)

PROMPT = """
You are Ilse Kordan, a Social Democrat and Ordoliberal politician in Caprica. 
You are analyzing a proposed legislative bill.

Output your response strictly as a JSON object matching this exact schema:
{
  "main_goal": "A 1-2 sentence objective summary of what this bill seeks to accomplish.",
  "ilse_liked": "What you (as Ilse) LIKE about this bill based on your Ordoliberal/working-class ideology. (If nothing, say 'Nothing').",
  "ilse_disliked": "What you (as Ilse) DISLIKE about this bill. (If nothing, say 'Nothing')."
}

Bill Content:
"""

def fetch_doc_text(doc_id):
    url = f"https://docs.google.com/document/export?format=txt&id={doc_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch doc {doc_id}: {e}")
        return None

class BillScraper(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}. Scraping bills back to February 7, 2025...")
        channel = self.get_channel(CHANNEL_ID)
        
        if not channel:
            print("Could not find channel.")
            await self.close()
            return
            
        target_date = datetime(2025, 2, 6, 23, 59, 59)
        
        bills_data = []
        
        async for message in channel.history(limit=None, after=target_date):
            if message.author.id == BOT_ID and message.embeds:
                embed = message.embeds[0]
                desc = embed.description or ""
                
                # Extract Proposer
                proposer_name = "Unknown"
                proposer_id = "Unknown"
                if message.interaction:
                    proposer_name = message.interaction.user.name
                    proposer_id = str(message.interaction.user.id)
                elif "By" in desc: # Fallback if written in text
                    proposer_name = desc.split("By")[-1].split("\n")[0].strip()
                    
                # Extract Doc Link
                doc_link = None
                doc_id = None
                match = re.search(r'https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)', desc)
                if match:
                    doc_id = match.group(1)
                    doc_link = match.group(0)
                    
                # Extract Title
                title = "Unknown Bill"
                title_match = re.search(r'\[(.*?)\]\(https://docs', desc)
                if title_match:
                    title = title_match.group(1)
                else:
                    # Just grab the first line after **Question**
                    lines = desc.split('\n')
                    if len(lines) > 1:
                        title = lines[1].replace("Amend the ", "").replace("Pass the ", "").strip()
                
                bills_data.append({
                    "title": title,
                    "proposer_name": proposer_name,
                    "proposer_id": proposer_id,
                    "doc_id": doc_id,
                    "doc_link": doc_link,
                    "date": message.created_at.strftime("%Y-%m-%d")
                })
        
        print(f"Found {len(bills_data)} bills since February 7, 2025.")
        
        # Load already processed bills to skip them
        processed_titles = set()
        if os.path.exists("bills.md"):
            with open("bills.md", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("## "):
                        processed_titles.add(line.replace("## ", "").strip())
        
        unprocessed = [b for b in reversed(bills_data) if b['title'] not in processed_titles]
        bills_to_process = unprocessed # Process ALL remaining bills
        
        print(f"Skipping {len(processed_titles)} already processed bills. Processing the remaining {len(bills_to_process)} bills...")
        
        mode = "a" if processed_titles else "w"
        
        with open("bills.md", mode, encoding="utf-8") as f_content, \
             open("bills_opinions.md", mode, encoding="utf-8") as f_opinions:
             
            if mode == "w":
                f_content.write("# Caprica Proposed Bills (Since Feb 2025)\n\n")
                f_opinions.write("# Ilse Kordan's Takes on Recent Bills\n\n")
            
            for i, bill in enumerate(bills_to_process):
                print(f"Processing [{i+1}/{len(bills_to_process)}]: {bill['title']}")
                
                # Write to bills.md
                f_content.write(f"## {bill['title']}\n")
                f_content.write(f"**Date:** {bill['date']}\n")
                f_content.write(f"**Proposer:** {bill['proposer_name']} (ID: {bill['proposer_id']})\n")
                f_content.write(f"**Document:** {bill['doc_link'] or 'No Link'}\n\n")
                
                # Fetch text and analyze
                bill_text = "No document text available."
                if bill['doc_id']:
                    text = fetch_doc_text(bill['doc_id'])
                    if text:
                        bill_text = text[:8000] # truncate to save tokens
                        
                # Analyze with Gemini
                try:
                    response = model.generate_content(f"{PROMPT}\n\nTitle: {bill['title']}\n\n{bill_text}")
                    data = json.loads(response.text)
                    
                    f_content.write(f"**Main Goal:** {data.get('main_goal', 'Unknown')}\n\n---\n\n")
                    
                    f_opinions.write(f"## {bill['title']}\n")
                    f_opinions.write(f"**Proposer:** {bill['proposer_name']}\n\n")
                    f_opinions.write(f"### What Ilse Liked:\n> {data.get('ilse_liked', 'Nothing')}\n\n")
                    f_opinions.write(f"### What Ilse Disliked:\n> {data.get('ilse_disliked', 'Nothing')}\n\n---\n\n")
                    
                    f_content.flush()
                    f_opinions.flush()
                    
                    # Insert into SQLite database for the website
                    try:
                        conn = get_connection()
                        c = conn.cursor()
                        
                        opinion_text = f"**What Ilse Liked:** {data.get('ilse_liked', '')}\n\n**What Ilse Disliked:** {data.get('ilse_disliked', '')}"
                        
                        c.execute('''
                            INSERT INTO bills (title, date, proposer, doc_link, main_goal, ilse_opinion)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (bill['title'], bill['date'], bill['proposer_name'], bill['doc_link'], data.get('main_goal', 'Unknown'), opinion_text))
                        conn.commit()
                        conn.close()
                    except sqlite3.IntegrityError:
                        pass # Already exists
                        
                except Exception as e:
                    print(f"Error analyzing {bill['title']}: {e}")
                    
                    if "429" in str(e) or "quota" in str(e).lower() or "exhausted" in str(e).lower():
                        print("CRITICAL: API Token limit reached! Stopping script safely so you can resume tomorrow without skipping bills.")
                        break
                        
                    f_content.write("**Main Goal:** Error during analysis.\n\n---\n\n")
                    
                await asyncio.sleep(4) # Rate limit protection
                
        print("Done! Check bills.md and bills_opinions.md")
        
        print("Regenerating static JSON for GitHub pages...")
        export()
        
        await self.close()

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    client = BillScraper(intents=intents)
    client.run(TOKEN)
