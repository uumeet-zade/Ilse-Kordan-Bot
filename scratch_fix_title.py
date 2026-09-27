import sqlite3, json

DB_PATH = 'data/memory.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("UPDATE bills SET title = 'Repeal the NGESAA' WHERE id = 712")
conn.commit()
conn.close()

with open('data/bills.json', 'r') as f:
    bills = json.load(f)

for b in bills:
    if b['id'] == 712:
        b['title'] = 'Repeal the NGESAA'

with open('data/bills.json', 'w') as f:
    json.dump(bills, f, indent=4)
