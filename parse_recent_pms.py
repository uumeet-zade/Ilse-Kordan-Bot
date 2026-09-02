from wiki import fetch_page_content
import re

content, _ = fetch_page_content('Prime Minister of Caprica')
if not content:
    print("Failed to fetch wiki content")
    exit(1)
    
lines = content.split('\n')
pms = []

for i in range(len(lines)):
    line = lines[i]
    if line.startswith('!'):
        if re.match(r'^!(\d+|\(-\))$', line.strip()):
            for j in range(i+1, min(len(lines), i+10)):
                name_match = re.search(r"\|(?:'''?)?\[\[([^\|\]]+)(?:\|[^\]]*)?\]\](?:'''?)?", lines[j])
                if name_match and "File:" not in name_match.group(1):
                    name = name_match.group(1)
                    name = name.replace("'''", "").strip()
                    if not pms or pms[-1] != name:
                        pms.append(name)
                    break

print("\nLast 5 PMs:")
for pm in pms[-5:]:
    print(pm)
