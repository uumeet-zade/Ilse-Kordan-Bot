import sys

with open("bot.py", "r") as f:
    content = f.read()

# Replace imports
content = content.replace("import json", "import json\nimport io\nfrom PIL import Image")

# Find the start of the block
start_str = """        print(f"[{time.strftime('%X')}] Received mention from {message.author.name}. Generating response...")"""
end_str = """            else:
                await wait_msg.edit(content=response)"""

import re
pattern = re.compile(re.escape(start_str) + r".*?" + re.escape(end_str), re.DOTALL)

replacement = """        print(f"[{time.strftime('%X')}] Received mention from {message.author.name}. Generating response...")
        await message.add_reaction("⏳")
        
        async with message.channel.typing():
            chat_history = ""
            async for msg in message.channel.history(limit=15, before=message):
                chat_history = f"{msg.author.name} (ID: {msg.author.id}): {msg.content}\\n" + chat_history
            
            # Fetch referenced message if replying to someone
            if message.reference and message.reference.message_id:
                try:
                    ref_msg = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                    chat_history = f"[CONTEXT - PINGER REPLIED TO THIS MESSAGE]\\n{ref_msg.author.name} (ID: {ref_msg.author.id}): {ref_msg.content}\\n[END CONTEXT]\\n\\n" + chat_history
                except Exception as e:
                    print(f"Failed to fetch referenced message: {e}")
                    
            # Check for image attachments
            image_data = None
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        try:
                            img_bytes = await attachment.read()
                            image_data = Image.open(io.BytesIO(img_bytes))
                            break
                        except Exception as e:
                            print(f"Failed to read image: {e}")
            
            is_test = (message.guild.id == TEST_SERVER_ID) if message.guild else False
            current_user_context = f"{message.author.name} (ID: {message.author.id})"
            
            response = await generate_response(message.content, chat_history, is_test_server=is_test, current_user=current_user_context, image_data=image_data)
            
            try:
                await message.remove_reaction("⏳", bot.user)
            except:
                pass
            
            # Check API Exhaustion
            if response == "<API_EXHAUSTED>":
                api_exhausted_until = time.time() + 60
                await message.reply("*(Ilse enters a state of rest. I have run out of API tokens and will ignore all requests for the next minute while my quota refreshes.)*")
                return

            if "<IGNORE>" in response:
                return
                
            # Check for AI-driven Ban
            if "<BLOCK_USER>" in response:
                if not is_owner_or_authorized(message.author):
                    ban_user(message.author.id)
                    await message.channel.send(f"I will not tolerate this conduct, {message.author.mention}.")
                    return
                else:
                    response = response.replace("<BLOCK_USER>", "")
                    
            # Check for AI-driven Strike (Slurs/Inappropriate)
            if "<STRIKE_USER>" in response:
                if not is_owner_or_authorized(message.author):
                    user_behavior_strikes[message.author.id] = user_behavior_strikes.get(message.author.id, 0) + 1
                    if user_behavior_strikes[message.author.id] >= 3:
                        ban_user(message.author.id)
                        await message.channel.send(f"You have been permanently banned for repeated infractions, {message.author.mention}.")
                        return
                    else:
                        await message.channel.send(f"I will not tolerate slurs, inappropriate conduct, or flirting, {message.author.mention}. (Strike {user_behavior_strikes[message.author.id]}/3)")
                        return
                else:
                    response = response.replace("<STRIKE_USER>", "")
            
            # Chunk response if > 2000 chars
            if len(response) > 2000:
                await message.reply(response[:1900])
                for chunk in [response[i:i+1900] for i in range(1900, len(response), 1900)]:
                    await message.channel.send(chunk)
            else:
                await message.reply(response)"""

new_content, count = pattern.subn(replacement, content)

if count == 1:
    with open("bot.py", "w") as f:
        f.write(new_content)
    print("Success")
else:
    print(f"Failed. Pattern count: {count}")
