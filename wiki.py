import json
import sqlite3
import subprocess
from database import get_connection, init_db

API_URL = "https://caprica.miraheze.org/w/api.php"

def curl_get_json(url):
    try:
        result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Curl error: {e}")
        return None

def fetch_all_pages():
    print("Fetching all article titles from Caprica Wiki...")
    pages = []
    apfrom = None
    
    while True:
        url = f"{API_URL}?action=query&list=allpages&apnamespace=0&aplimit=max&format=json"
        if apfrom:
            url += f"&apcontinue={apfrom}"
            
        response = curl_get_json(url)
        if not response or "query" not in response:
            print("Failed to fetch page list.")
            break
        
        for p in response["query"]["allpages"]:
            pages.append(p["title"])
            
        if "continue" in response and "apcontinue" in response["continue"]:
            apfrom = response["continue"]["apcontinue"]
        else:
            break
            
    return pages

def fetch_page_content(title):
    # URL encode the title for curl
    import urllib.parse
    encoded_title = urllib.parse.quote(title)
    url = f"{API_URL}?action=query&prop=revisions&rvprop=content|timestamp&titles={encoded_title}&format=json"
    
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

def search_live_wiki(query):
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    url = f"{API_URL}?action=query&list=search&srsearch={encoded_query}&format=json"
    
    response = curl_get_json(url)
    if not response or "query" not in response or "search" not in response["query"]:
        return []
        
    return [item["title"] for item in response["query"]["search"][:3]]

def ingest_wiki():
    init_db()
    conn = get_connection()
    c = conn.cursor()
    
    titles = fetch_all_pages()
    print(f"Found {len(titles)} articles. Starting download...")
    
    count = 0
    for title in titles:
        # To avoid hitting rate limits too hard, we could sleep, but MediaWiki is usually fine with sequential requests.
        content, timestamp = fetch_page_content(title)
        if content:
            c.execute(
                "INSERT OR REPLACE INTO wiki_pages (title, content, last_updated) VALUES (?, ?, ?)",
                (title, content, timestamp)
            )
            count += 1
            if count % 50 == 0:
                print(f"Downloaded {count}/{len(titles)} pages...")
                conn.commit()
                
    conn.commit()
    conn.close()
    print(f"Ingestion complete. {count} pages saved to local database (Brain B).")

if __name__ == "__main__":
    ingest_wiki()
