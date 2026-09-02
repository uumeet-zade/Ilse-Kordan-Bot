from wiki import fetch_page_content
import re

content, _ = fetch_page_content('Prime Minister of Caprica')

# Try to extract the last 5 PMs based on chronological ordering in the first table
lines = content.split('\n')
pms = []
in_table = False

for line in lines:
    if '!' in line and not in_table:
        if re.match(r'^!\(?-?\d+\)?$', line.strip()):
            in_table = True
    if in_table:
        name_match = re.search(r"\|(?:'''?)?\[\[([^\|\]]+)(?:\|[^\]]*)?\]\](?:'''?)?", line)
        if name_match and "File:" not in name_match.group(1):
            name = name_match.group(1)
            # Remove any trailing apostrophes or bolding if it leaked
            name = name.replace("'''", "").strip()
            # Only add if it's not the same as the last one (acting PMs etc)
            if not pms or pms[-1] != name:
                pms.append(name)
            in_table = False

# The first table should list them in order. Let's see the last 10 just to be sure.
print(pms[-10:])
