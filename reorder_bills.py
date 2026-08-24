import sqlite3

def regenerate():
    conn = sqlite3.connect('memory.db')
    conn.row_factory = sqlite3.Row
    bills = conn.execute('SELECT * FROM bills ORDER BY date DESC, id DESC').fetchall()
    
    with open('bills.md', 'w', encoding='utf-8') as f:
        f.write("# Caprica Proposed Bills (Sorted by Date)\n\n")
        for bill in bills:
            doc_link = bill['doc_link'] if bill['doc_link'] else "No Link"
            f.write(f"## {bill['title']}\n")
            f.write(f"**Date:** {bill['date']}\n")
            f.write(f"**Proposer:** {bill['proposer']}\n")
            f.write(f"**Document:** {doc_link}\n\n")
            f.write(f"**Main Goal:** {bill['main_goal']}\n\n---\n\n")

    print(f"Regenerated bills.md with {len(bills)} bills sorted by date.")
    conn.close()

if __name__ == "__main__":
    regenerate()
