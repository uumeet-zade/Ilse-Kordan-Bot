from wiki import fetch_page_content
import re

content, _ = fetch_page_content('Prime Minister of Caprica')
if not content:
    print("Failed to fetch")
    exit(1)

# Extract the list of PMs from the wikitext
pms = []
lines = content.split('\n')
in_table = False
current_pm = None

for line in lines:
    # Basic logic to find the main PM table rows
    if '!' in line and not in_table:
        # Check if it looks like a number in the table (e.g. !19 or !18)
        if re.match(r'^!\(?-?\d+\)?$', line.strip()):
            in_table = True
            
    if in_table:
        # Look for the name row which usually starts with a bold tag like |'''[[Name]]'''
        name_match = re.search(r"\|'''?\[\[([^\|\]]+)(?:\|[^\]]*)?\]\]'''?", line)
        if name_match:
            current_pm = name_match.group(1)
            pms.append(current_pm)
            in_table = False # Reset to wait for the next row

print(pms)
