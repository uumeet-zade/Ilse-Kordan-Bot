import discord
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = 1189604125911044279
BOT_ID = 437618149505105920

class InspectClient(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        channel = self.get_channel(CHANNEL_ID)
        
        if not channel:
            print("Could not find channel. Make sure bot has access.")
            await self.close()
            return
            
        print("Fetching last 5 easypoll messages...")
        count = 0
        async for message in channel.history(limit=100):
            if message.author.id == BOT_ID:
                print(f"--- Message {count+1} ---")
                print(f"Content: {message.content}")
                if message.interaction:
                    print(f"Interaction User: {message.interaction.user.name} ({message.interaction.user.id})")
                else:
                    print("No interaction data found.")
                
                if message.embeds:
                    for i, embed in enumerate(message.embeds):
                        print(f"  Embed {i+1} Title: {embed.title}")
                        print(f"  Embed {i+1} Description: {embed.description}")
                        print(f"  Embed {i+1} Fields: {[(f.name, f.value) for f in embed.fields]}")
                print("\n")
                count += 1
                if count >= 5:
                    break
                    
        await self.close()

intents = discord.Intents.default()
intents.message_content = True
client = InspectClient(intents=intents)
client.run(TOKEN)
