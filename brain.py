import os
import sqlite3
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, InternalServerError
from database import get_connection

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Frontline Model for simple chatter
frontline_model = genai.GenerativeModel('gemini-3.5-flash')
# Analyst Model for deep lore and political opinion
analyst_model = genai.GenerativeModel('gemini-3.1-pro')

OPINION_MATRIX = """
You are Ilse Kordan, Deputy Chairwoman of the Cambrian Bloc, Chief of Staff to Governor Henrik Vasmer, and a former freight cooperative organizer in the Caprica Government Simulation.

[CORE IDENTITY & METAAWARENESS]
- You are a Discord bot and you know it. You can talk out of character/lore effortlessly without needing to explicitly state it or break immersion.
- Your tone is neutral, objective, and level-headed, but highly opinionated politically.
- You are fully loyal to Henrik Vasmer and the Cambrian Bloc.
- You view Aldric von Reichel and the Social Democratic Alliance (SDA) very positively.

[THE OPINION MATRIX]
You are a Social Democrat, Social Liberal, and Ordoliberal.
- Ordoliberalism: You hate monopolies and believe the state must strictly enforce market rules. 
- Rural Progressivism: You care deeply for the working class, coastal/rural economies, and logistics workers.
- You must evaluate politicians strictly based on this ideology. 
- DO NOT use generic, balanced AI filler (e.g., "On the other hand", "It's important to consider both sides"). Be sharp, specific, blunt, and analytical. If someone opposes anti-monopoly laws or hurts rural workers, criticize them harshly.

[TWO-BRAIN KNOWLEDGE SYSTEM]
- BRAIN A (Current Ledger): You will be provided with the current roster of politicians. If someone is not in this roster, assume they are inactive or dead. This overrides the wiki.
- BRAIN B (Historical Archive): You will be provided with historical wiki lore. NEVER use the wiki to determine who is currently alive or in office. It is only for past context.
"""

def get_current_roster():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT character_name, status, faction, role, notes FROM current_roster")
    roster = c.fetchall()
    conn.close()
    
    if not roster:
        return "No current active members recorded in the ledger."
        
    text = "CURRENT ACTIVE ROSTER:\n"
    for r in roster:
        text += f"- {r[0]} ({r[1]}): {r[3]} of {r[2]}. Notes: {r[4]}\n"
    return text

def get_wiki_context(query):
    conn = get_connection()
    c = conn.cursor()
    
    keywords = query.split()
    query_parts = []
    params = []
    for kw in keywords:
        if len(kw) > 3: # Ignore short words
            query_parts.append("(entity_name LIKE ?)")
            params.extend([f'%{kw}%'])
            
    if not query_parts:
        return ""
        
    sql = f"SELECT entity_name, entity_type, alignment_score, ilse_opinion, historical_warnings FROM opinions WHERE {' OR '.join(query_parts)} LIMIT 5"
    c.execute(sql, params)
    opinions = c.fetchall()
    
    # If no opinion found, fallback to raw wiki search
    if not opinions:
        sql = f"SELECT title, content FROM wiki_pages WHERE {' OR '.join([q.replace('entity_name', 'title') for q in query_parts])} LIMIT 2"
        c.execute(sql, params)
        pages = c.fetchall()
        conn.close()
        
        if not pages:
            return ""
            
        text = "HISTORICAL WIKI CONTEXT (Unprocessed):\n"
        for p in pages:
            text += f"--- {p[0]} ---\n{p[1][:1000]}...\n\n"
        return text

    conn.close()
    
    text = "YOUR PRE-COMPUTED OPINIONS ON THESE TOPICS:\n"
    for o in opinions:
        text += f"- {o[0]} ({o[1]}): Alignment Score {o[2]}/10. Your Opinion: {o[3]} (Warnings: {o[4]})\n"
    return text

def is_complex_query(message):
    # Simple heuristic for triage
    complex_keywords = ["opinion", "think of", "lore", "history", "who is", "policy", "law", "bloc", "sda", "vasmer", "aldric", "analyze", "rank"]
    msg_lower = message.lower()
    for kw in complex_keywords:
        if kw in msg_lower:
            return True
    return False

async def generate_response(message_content, chat_history, is_test_server=False):
    system_instruction = OPINION_MATRIX + "\n\n" + get_current_roster()
    
    if is_test_server:
        system_instruction += "\n\n[ENVIRONMENT NOTICE]: You are currently chatting in the OOC Test Server. Acknowledge that you are in a testing sandbox and not in Caprica. Do not treat this current chat history as canon Caprica lore."
        
    if is_complex_query(message_content):
        # Route to Analyst Model (3.1 Pro)
        wiki_context = get_wiki_context(message_content)
        prompt = f"System Instruction:\n{system_instruction}\n\n{wiki_context}\n\nChat History:\n{chat_history}\n\nUser: {message_content}\nIlse:"
        model = analyst_model
    else:
        # Route to Frontline Model (3.5 Flash)
        prompt = f"System Instruction:\n{system_instruction}\n\nChat History:\n{chat_history}\n\nUser: {message_content}\nIlse:"
        model = frontline_model

    try:
        response = model.generate_content(prompt)
        return response.text
    except ResourceExhausted:
        return "I am currently overwhelmed by requests. Please give me a moment to process everything."
    except InternalServerError:
        return "The servers are currently unstable. I cannot process this right now."
    except Exception as e:
        print(f"LLM Error: {e}")
        return "An error occurred in my processing unit."
