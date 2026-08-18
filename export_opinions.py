import sqlite3
import os
from database import get_connection

def export_opinions():
    artifact_path = "/Users/umidgasimzade/.gemini/antigravity-ide/brain/c13ba9ab-0dff-40a2-90f1-4cd72e7bfb29/ilse_opinions.md"
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT entity_name, entity_type, alignment_score, ilse_opinion FROM opinions WHERE entity_type != 'Empty' ORDER BY alignment_score DESC")
    opinions = c.fetchall()
    conn.close()
    
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write("# Ilse Kordan's Ideological Opinions Database\n\n")
        f.write("This document contains every opinion Ilse has formed during her Deep Study phase, sorted by her ideological alignment score (10.0 being a perfect Ordoliberal/Social Democrat match).\n\n")
        
        for op in opinions:
            f.write(f"### {op[0]} ({op[1]})\n")
            f.write(f"**Alignment Score:** {op[2]}/10\n\n")
            f.write(f"> {op[3]}\n\n")
            f.write("---\n\n")
            
    print(f"Successfully exported {len(opinions)} opinions to artifact.")

if __name__ == "__main__":
    export_opinions()
