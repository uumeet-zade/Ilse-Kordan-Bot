import requests, os
from dotenv import load_dotenv

load_dotenv("config/.env")
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = "1189604125911044279"

headers = {
    "Authorization": f"Bot {TOKEN}"
}
url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages/1552098461120331877"
response = requests.get(url, headers=headers)
if response.status_code == 200:
    msg = response.json()
    print(f"Message ID: {msg.get('id')}")
    print(f"Components: {msg.get('components', [])}")
    print(f"Reactions: {msg.get('reactions', [])}")
else:
    print(f"Error {response.status_code}: {response.text}")
