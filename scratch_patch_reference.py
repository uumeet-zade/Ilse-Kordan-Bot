import re

with open("src/bot.py", "r") as f:
    code = f.read()

# The current code:
old_ref_logic = """                # Fetch referenced message if replying to someone
                if message.reference and message.reference.message_id:
                    try:
                        ref_msg = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                        chat_history = f"[CONTEXT - PINGER REPLIED TO THIS MESSAGE]\\n{ref_msg.author.display_name} (Username: {ref_msg.author.name}, ID: {ref_msg.author.id}): {ref_msg.content}\\n[END CONTEXT]\\n\\n" + chat_history
                    except Exception as e:
                        print(f"Failed to fetch referenced message: {e}")"""

new_ref_logic = """                # Fetch referenced message if replying to someone
                modified_message_content = message.content
                if message.reference and message.reference.message_id:
                    try:
                        ref_msg = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                        modified_message_content = f"[NOTE: The user is explicitly replying to the following message: '{ref_msg.content}' by {ref_msg.author.display_name}. Please take this replied message directly into account.]\\n\\n" + message.content
                    except Exception as e:
                        print(f"Failed to fetch referenced message: {e}")"""

code = code.replace(old_ref_logic, new_ref_logic)

# Replace the call to generate_response to use modified_message_content
old_call = "response = await generate_response(message.content, chat_history,"
new_call = "response = await generate_response(modified_message_content, chat_history,"
code = code.replace(old_call, new_call)

with open("src/bot.py", "w") as f:
    f.write(code)
