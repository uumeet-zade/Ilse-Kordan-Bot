import requests, os
from dotenv import load_dotenv

load_dotenv("config/.env")
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = "1189604125911044279"

headers = {
    "Authorization": f"Bot {TOKEN}"
}
url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=15"
response = requests.get(url, headers=headers)
if response.status_code == 200:
    messages = response.json()
    for msg in messages:
        print(f"[{msg['id']}] {msg['author']['username']}: {msg.get('content')}")
        for e in msg.get('embeds', []):
            print(f"  Embed: {e.get('description', '')[:50]}")
else:
    print(f"Error {response.status_code}: {response.text}")
