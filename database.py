import sqlite3
import os
import json

DB_PATH = 'memory.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Brain B: Historical Archive (The Wiki)
    c.execute('''
        CREATE TABLE IF NOT EXISTS wiki_pages (
            title TEXT PRIMARY KEY,
            content TEXT,
            last_updated TEXT
        )
    ''')
    
    # Brain A: Current State Ledger
    c.execute('''
        CREATE TABLE IF NOT EXISTS current_roster (
            character_name TEXT PRIMARY KEY,
            status TEXT,
            faction TEXT,
            role TEXT,
            notes TEXT
        )
    ''')
    
    # Discord Context Buffer
    c.execute('''
        CREATE TABLE IF NOT EXISTS discord_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            author TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Deep Study Opinions (Structured JSON Data)
    c.execute('''
        CREATE TABLE IF NOT EXISTS opinions (
            entity_name TEXT PRIMARY KEY,
            entity_type TEXT,
            alignment_score REAL,
            ilse_opinion TEXT,
            historical_warnings TEXT
        )
    ''')
    
    # Caprican Bills Archive
    c.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            date TEXT,
            proposer TEXT,
            doc_link TEXT,
            main_goal TEXT,
            ilse_opinion TEXT,
            UNIQUE(title)
        )
    ''')
    
    # Regional Bills Archive
    c.execute('''
        CREATE TABLE IF NOT EXISTS regional_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            region TEXT,
            date TEXT,
            proposer TEXT,
            doc_link TEXT,
            UNIQUE(doc_link)
        )
    ''')
    
    # Discord Lore Archive
    c.execute('''
        CREATE TABLE IF NOT EXISTS discord_lore (
            message_id TEXT PRIMARY KEY,
            channel_name TEXT,
            thread_name TEXT,
            author TEXT,
            content TEXT,
            timestamp DATETIME
        )
    ''')
    
    # System Status for Website
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_heartbeat REAL,
            last_update REAL
        )
    ''')
    
    # Insert default status if empty
    c.execute('INSERT OR IGNORE INTO system_status (id, last_heartbeat, last_update) VALUES (1, 0, 0)')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
