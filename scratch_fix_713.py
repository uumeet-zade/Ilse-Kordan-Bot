import sqlite3, json

DB_PATH = 'data/memory.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
doc_url = 'https://docs.google.com/document/d/1HXM9yvarH3Ku5KiXB8BumI76Jb_tvPAvbaMydtxXnMw/edit?tab=t.0'
title = 'Public Response Agency Act of 2069'

c.execute("UPDATE bills SET title = ?, doc_link = ? WHERE id = 713", (title, doc_url))
conn.commit()
conn.close()

with open('data/bills.json', 'r') as f:
    bills = json.load(f)

for b in bills:
    if b['id'] == 713:
        b['title'] = title
        b['doc_link'] = doc_url

with open('data/bills.json', 'w') as f:
    json.dump(bills, f, indent=4)
