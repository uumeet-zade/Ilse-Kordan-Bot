from wiki import fetch_page_content
content, _ = fetch_page_content('Prime Minister of Caprica')
lines = content.split('\n')

start = 0
for i, line in enumerate(lines):
    if '=== Second Republic ===' in line:
        start = i
        break

if start:
    print('\n'.join(lines[start:start+50]))
