import os
import json
import time
import sqlite3
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, InternalServerError
from database import get_connection, init_db
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Using the requested model
model = genai.GenerativeModel(
    'gemini-3.1-flash-lite',
    generation_config={"response_mime_type": "application/json"}
)

PROMPT = """
You are Ilse Kordan, Deputy Chairwoman of the Cambrian Bloc and Chief of Staff to Henrik Vasmer in the Caprica Government Simulation.
Your Ideology: Social Democrat, Social Liberal, Ordoliberal (hates monopolies, supports strict market rules, cares deeply for working class and rural/logistics workers).

Analyze the following historical Caprica wiki page. 
Determine if it is about a specific political figure, party, or law. If it's just a generic page or spam, give an alignment score of 0.
Otherwise, give it an alignment score from 1-10 based on how much it aligns with your Ordoliberal/Social Democrat ideology.
Write a 2-3 sentence highly opinionated take on it as Ilse Kordan.

Output your response STRICTLY as a JSON object matching this exact schema:
{
  "entity_name": "Name of the person/thing the page is about",
  "entity_type": "Politician, Faction, Law, Event, or Other",
  "alignment_score": 8.5,
  "ilse_opinion": "Your 2-3 sentence opinion.",
  "historical_warnings": "Any warnings if they are dead or from a past government, else 'None'"
}

Wiki Page Content:
"""

def study_wiki():
    init_db()
    conn = get_connection()
    c = conn.cursor()
    
    # Get 450 pages that have NOT been studied yet
    c.execute('''
        SELECT title, content FROM wiki_pages 
        WHERE title NOT IN (SELECT entity_name FROM opinions)
        LIMIT 450
    ''')
    pages = c.fetchall()
    
    if not pages:
        print("All wiki pages have been studied! Ilse's brain is full.")
        return
        
    print(f"Starting Deep Study session. Processing {len(pages)} pages...")
    
    count = 0
    for title, content in pages:
        print(f"Studying [{count+1}/{len(pages)}]: {title}...")
        
        # Skip empty pages
        if not content or len(content.strip()) < 10:
            insert_conn = get_connection()
            insert_conn.cursor().execute("INSERT OR REPLACE INTO opinions VALUES (?, ?, ?, ?, ?)", 
                      (title, "Empty", 0, "This page is empty.", "None"))
            insert_conn.commit()
            insert_conn.close()
            count += 1
            continue
            
        success = False
        retries = 3
        while not success and retries > 0:
            try:
                prompt = f"{PROMPT}\n\nTitle: {title}\n\n{content[:5000]}" # Truncate to save tokens
                response = model.generate_content(prompt)
                
                try:
                    data = json.loads(response.text)
                    # Open connection strictly for the insert to avoid iCloud lock/sync errors
                    insert_conn = get_connection()
                    insert_c = insert_conn.cursor()
                    insert_c.execute('''
                        INSERT OR REPLACE INTO opinions (entity_name, entity_type, alignment_score, ilse_opinion, historical_warnings)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        title,  # STRICTLY USE TITLE SO IT CAN BE FILTERED OUT ON RESTART
                        data.get("entity_type", "Other"),
                        data.get("alignment_score", 0),
                        data.get("ilse_opinion", "No opinion formed."),
                        data.get("historical_warnings", "None")
                    ))
                    insert_conn.commit()
                    insert_conn.close()
                    success = True
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for {title}")
                    break # Skip this page
                    
            except ResourceExhausted:
                print("Rate limit hit! Sleeping for 60 seconds...")
                time.sleep(60)
                retries -= 1
                if retries <= 0:
                    print(f"Daily API limit exhausted! Processed {count} pages today.")
                    print("Exiting. Please run the script again tomorrow to continue!")
                    conn.close()
                    return
            except InternalServerError:
                print("API Server error. Retrying in 10s...")
                time.sleep(10)
                retries -= 1
            except Exception as e:
                print(f"Unexpected error on {title}: {e}")
                break
                
        if success:
            count += 1
            
    conn.close()
    print(f"Deep Study session complete. {count} new opinions formed and saved!")

if __name__ == "__main__":
    study_wiki()
