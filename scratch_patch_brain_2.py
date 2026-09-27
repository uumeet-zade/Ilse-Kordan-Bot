import re

with open("src/brain.py", "r") as f:
    brain_code = f.read()

# Update signature
brain_code = brain_code.replace(
    'async def generate_response(message_content, chat_history, is_test_server=False, current_user="Unknown User", image_data=None, force_model=None, linked_messages_context=None, discord_bot=None):',
    'async def generate_response(message_content, chat_history, is_test_server=False, current_user="Unknown User", image_data=None, force_model=None, linked_messages_context=None, discord_bot=None, is_general_chat=False):'
)

# Add prompt injection
injection = """
        if is_test_server:
            system_prompt += "\n\n(OOC: You are currently talking in the test server. You can break character slightly if asked about technical things, but generally remain in character.)"
        
        if is_general_chat:
            system_prompt += "\n\nCRITICAL INSTRUCTION: You are currently responding in the general chat. Keep your response extremely brief, around the length of a tweet (maximum 280 characters). Do not write long paragraphs."
"""

brain_code = brain_code.replace(
    '        if is_test_server:\n            system_prompt += "\\n\\n(OOC: You are currently talking in the test server. You can break character slightly if asked about technical things, but generally remain in character.)"',
    injection
)

with open("src/brain.py", "w") as f:
    f.write(brain_code)

with open("src/bot.py", "r") as f:
    bot_code = f.read()

bot_code = bot_code.replace("ALLOWED_CAPRICA_CHANNELS = [1266040682213281955]", "ALLOWED_CAPRICA_CHANNELS = [1266040682213281955, 1189630582280441997]")

# Update is_allowed_channel
is_allowed_old = """def is_allowed_channel(message):
    guild_id = message.guild.id if message.guild else None
    if guild_id == TEST_SERVER_ID:
        return True
    if guild_id == CAPRICA_SERVER_ID and message.channel.id in ALLOWED_CAPRICA_CHANNELS:
        return True
    return False"""

is_allowed_new = """def is_allowed_channel(message):
    guild_id = message.guild.id if message.guild else None
    if guild_id == TEST_SERVER_ID:
        return True
    if guild_id == CAPRICA_SERVER_ID:
        if message.channel.id == 1189630582280441997:
            if is_owner_or_authorized(message.author):
                return True
            return False
        if message.channel.id in ALLOWED_CAPRICA_CHANNELS:
            return True
    return False"""

bot_code = bot_code.replace(is_allowed_old, is_allowed_new)

# Update generate_response calls in bot.py
bot_code = bot_code.replace(
    'response = await generate_response(query, chat_history, is_test_server=is_test, current_user=current_user_context, image_data=None, force_model="glm-5-2", linked_messages_context=linked_context, discord_bot=bot)',
    'response = await generate_response(query, chat_history, is_test_server=is_test, current_user=current_user_context, image_data=None, force_model="glm-5-2", linked_messages_context=linked_context, discord_bot=bot, is_general_chat=(interaction.channel_id == 1189630582280441997))'
)

bot_code = bot_code.replace(
    'response = await generate_response(query, chat_history, is_test_server=is_test, current_user=current_user_context, image_data=None, linked_messages_context=linked_context, discord_bot=bot)',
    'response = await generate_response(query, chat_history, is_test_server=is_test, current_user=current_user_context, image_data=None, linked_messages_context=linked_context, discord_bot=bot, is_general_chat=(interaction.channel_id == 1189630582280441997))'
)

bot_code = bot_code.replace(
    'response = await generate_response(message.content, chat_history, is_test_server=is_test, current_user=current_user_context, image_data=image_data, linked_messages_context=linked_context, discord_bot=bot)',
    'response = await generate_response(message.content, chat_history, is_test_server=is_test, current_user=current_user_context, image_data=image_data, linked_messages_context=linked_context, discord_bot=bot, is_general_chat=(message.channel.id == 1189630582280441997))'
)

with open("src/bot.py", "w") as f:
    f.write(bot_code)
