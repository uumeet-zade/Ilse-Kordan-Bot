import sqlite3, json, os

DB_PATH = 'data/memory.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("UPDATE bills SET votes_yay = NULL, votes_nay = NULL, votes_abstain = NULL, votes_absent = NULL WHERE id IN (708, 709)")
conn.commit()
conn.close()

with open('data/bills.json', 'r') as f:
    bills = json.load(f)

for b in bills:
    if b['id'] in (708, 709):
        b['votes_yay'] = None
        b['votes_nay'] = None
        b['votes_abstain'] = None
        b['votes_absent'] = None

with open('data/bills.json', 'w') as f:
    json.dump(bills, f, indent=4)
