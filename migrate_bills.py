import sqlite3
import re
from database import get_connection

def parse_bills():
    bills_data = {}
    
    # Parse bills.md
    try:
        with open("bills.md", "r", encoding="utf-8") as f:
            content = f.read()
            
        blocks = content.split("## ")[1:]
        for block in blocks:
            lines = block.strip().split("\n")
            title = lines[0].strip()
            
            date = ""
            proposer = ""
            doc_link = ""
            main_goal = ""
            
            goal_started = False
            for line in lines[1:]:
                if line.startswith("**Date:**"):
                    date = line.replace("**Date:**", "").strip()
                elif line.startswith("**Proposer:**"):
                    proposer = line.replace("**Proposer:**", "").strip()
                elif line.startswith("**Document:**"):
                    doc_link = line.replace("**Document:**", "").strip()
                elif line.startswith("**Main Goal:**"):
                    main_goal = line.replace("**Main Goal:**", "").strip()
                    goal_started = True
                elif goal_started and not line.startswith("---"):
                    if line.strip():
                        main_goal += " " + line.strip()
                        
            bills_data[title] = {
                "title": title,
                "date": date,
                "proposer": proposer,
                "doc_link": doc_link,
                "main_goal": main_goal,
                "ilse_opinion": ""
            }
    except FileNotFoundError:
        print("bills.md not found.")

    # Parse bills_opinions.md
    try:
        with open("bills_opinions.md", "r", encoding="utf-8") as f:
            content = f.read()
            
        blocks = content.split("## ")[1:]
        for block in blocks:
            lines = block.strip().split("\n")
            title = lines[0].strip()
            
            if title in bills_data:
                # Extract opinion sections
                liked = ""
                disliked = ""
                
                mode = None
                for line in lines[1:]:
                    if "### What Ilse Liked:" in line:
                        mode = "liked"
                    elif "### What Ilse Disliked:" in line:
                        mode = "disliked"
                    elif line.startswith("---"):
                        break
                    elif mode == "liked" and line.startswith(">"):
                        liked += line.replace(">", "").strip() + " "
                    elif mode == "disliked" and line.startswith(">"):
                        disliked += line.replace(">", "").strip() + " "
                
                opinion = f"**What Ilse Liked:** {liked.strip()}\n\n**What Ilse Disliked:** {disliked.strip()}"
                bills_data[title]["ilse_opinion"] = opinion
    except FileNotFoundError:
        print("bills_opinions.md not found.")

    return list(bills_data.values())

def migrate():
    bills = parse_bills()
    print(f"Found {len(bills)} bills to migrate.")
    
    conn = get_connection()
    c = conn.cursor()
    
    count = 0
    for bill in bills:
        try:
            c.execute('''
                INSERT INTO bills (title, date, proposer, doc_link, main_goal, ilse_opinion)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (bill['title'], bill['date'], bill['proposer'], bill['doc_link'], bill['main_goal'], bill['ilse_opinion']))
            count += 1
        except sqlite3.IntegrityError:
            pass # Already exists
            
    conn.commit()
    conn.close()
    
    print(f"Successfully migrated {count} bills into the database.")

if __name__ == "__main__":
    migrate()
