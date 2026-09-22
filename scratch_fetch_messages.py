import discord, os, asyncio
from dotenv import load_dotenv

load_dotenv("config/.env")
TOKEN = os.getenv("DISCORD_TOKEN")
VOTING_CHANNEL_ID = 1111666996681424916

class MyClient(discord.Client):
    async def on_ready(self):
        channel = await self.fetch_channel(VOTING_CHANNEL_ID)
        print("Fetching messages...")
        messages = []
        async for msg in channel.history(limit=5):
            messages.append(msg)
            
        for msg in messages:
            print(f"Message ID: {msg.id}")
            if msg.embeds:
                for idx, embed in enumerate(msg.embeds):
                    print(f"Embed {idx} Title: {embed.title}")
                    print(f"Embed {idx} Desc: {repr(embed.description)}")
            else:
                print(f"Content: {msg.content}")
            print("-" * 50)
            
        await self.close()

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run(TOKEN)
