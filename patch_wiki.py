import os

with open("wiki.py", "r") as f:
    content = f.read()

# Replace fetch_page_content with curl-based implementation
content = content.replace('''
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
'''.strip(), '''
def fetch_page_content(title):
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
'''.strip())

with open("wiki.py", "w") as f:
    f.write(content)

print("patched")
