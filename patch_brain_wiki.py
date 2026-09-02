import os

with open("brain.py", "r") as f:
    content = f.read()

content = content.replace(
    'CRITICAL INSTRUCTION FOR SEARCHING: Extract ONLY the core, full name from the user\\\'s prompt. DO NOT include acronyms in parentheses. For example, if the user asks about "New Jersey Roundhead (NJR)", search EXACTLY for "New Jersey Roundhead". Do not search for "NJR" or "new jersey roundhead NJR". Keep your query as simple and broad as possible.',
    'CRITICAL INSTRUCTION FOR SEARCHING: Extract ONLY the core, full name from the user\\\'s prompt. DO NOT include acronyms in parentheses. Keep your query as simple and broad as possible. If the user asks about "Prime Ministers of Caprica", use exactly "Prime Minister of Caprica" as the search query.'
)

with open("brain.py", "w") as f:
    f.write(content)

print("patched")
