import subprocess
import json
import urllib.parse
import re

def curl_get_json(url):
    try:
        result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Curl error: {e}")
        return None

def fetch_page_content(title):
    encoded_title = urllib.parse.quote(title)
    url = f"https://caprica.miraheze.org/w/api.php?action=query&prop=revisions&rvprop=content|timestamp&titles={encoded_title}&format=json"
    
    response = curl_get_json(url)
    if not response or "query" not in response or "pages" not in response["query"]:
        return None, None
        
    pages = response["query"]["pages"]
    for page_id in pages:
        if page_id == "-1":
            return None, None
        try:
            rev = pages[page_id]["revisions"][0]
            return rev["*"], rev["timestamp"]
        except (KeyError, IndexError):
            return None, None
    return None, None

content, _ = fetch_page_content('Prime Minister of Caprica')
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

print("\n".join(pms[-5:]))
