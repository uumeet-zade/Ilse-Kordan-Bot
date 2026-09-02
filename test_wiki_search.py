import subprocess
import json

def curl_get_json(url):
    try:
        result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Curl error: {e}")
        return None

def search_live_wiki(query):
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    url = f"https://caprica.miraheze.org/w/api.php?action=query&list=search&srsearch={encoded_query}&format=json"
    
    response = curl_get_json(url)
    if not response or "query" not in response or "search" not in response["query"]:
        return []
        
    return [item["title"] for item in response["query"]["search"]]

print(search_live_wiki('Prime Minister of Caprica'))
