import subprocess
import json
import urllib.parse

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

content, ts = fetch_page_content('Prime Minister of Caprica')
print(content[-1500:] if content else "None")
