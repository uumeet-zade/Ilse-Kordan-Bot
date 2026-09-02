import os

with open("brain.py", "r") as f:
    content = f.read()

content = content.replace(
    '"description": "Searches the live Caprica Miraheze wiki for lore, people, governments, and bills. Extract ONLY the core, full name from the user\\'s prompt."',
    '"description": "Searches the live Caprica Miraheze wiki for lore, people, governments, and bills. Extract ONLY the core, full name from the user\\'s prompt. Keep the query simple. If the user asks about \\"Prime Ministers of Caprica\\", use exactly \\"Prime Minister of Caprica\\" as the query."'
)

with open("brain.py", "w") as f:
    f.write(content)

print("patched")
