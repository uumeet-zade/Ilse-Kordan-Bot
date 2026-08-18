import sqlite3
from database import get_connection

def view_opinions():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT entity_name, entity_type, alignment_score, ilse_opinion FROM opinions WHERE entity_type != 'Empty' ORDER BY alignment_score DESC")
    opinions = c.fetchall()
    
    if not opinions:
        print("Ilse hasn't formed any opinions yet! Run ./study_wiki.sh first.")
        return
        
    print(f"--- ILSE's CURRENT OPINIONS ({len(opinions)} total) ---\n")
    for op in opinions:
        print(f"[{op[2]}/10] {op[0]} ({op[1]})")
        print(f"  Opinion: {op[3]}\n")
        
    conn.close()

if __name__ == "__main__":
    view_opinions()
