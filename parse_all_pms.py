from wiki import fetch_page_content
import re

content, _ = fetch_page_content('Prime Minister of Caprica')

lines = content.split('\n')
pms = []
in_table = False

for i, line in enumerate(lines):
    if '!' in line and not in_table:
        if re.match(r'^!\(?-?\d+\)?$', line.strip()):
            in_table = True
    if in_table:
        name_match = re.search(r"\|(?:'''?)?\[\[([^\|\]]+)(?:\|[^\]]*)?\]\](?:'''?)?", line)
        if name_match and "File:" not in name_match.group(1):
            name = name_match.group(1)
            name = name.replace("'''", "").strip()
            if not pms or pms[-1] != name:
                pms.append(name)
            in_table = False

# Now let's refine this to specifically pick out from the 10th PM to the 19th PM
for i, line in enumerate(lines):
    if 'Rachel Edelstein-Powell' in line or 'Mandy Trottier' in line or 'Kosta Piastri' in line:
        start = max(0, i-5)
        end = min(len(lines), i+5)

print("\nLast PMs in Order (Table 1):")
for idx, pm in enumerate(pms):
    print(f"{idx+1}. {pm}")
