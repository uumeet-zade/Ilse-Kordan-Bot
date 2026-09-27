with open("src/bot.py", "r") as f:
    code = f.read()

think_start = """@bot.tree.command(name="think", description="Run a deep analysis query using the flagship GLM-5-2 model.")
async def think_command(interaction: discord.Interaction, query: str):
    if is_banned(interaction.user.id):
        await interaction.response.send_message("You are not authorized to use this bot.", ephemeral=True)
        return
        
    guild_id = interaction.guild.id if interaction.guild else None
    if guild_id != TEST_SERVER_ID and (guild_id != CAPRICA_SERVER_ID or interaction.channel_id not in ALLOWED_CAPRICA_CHANNELS):
        await interaction.response.send_message("I am currently restricted from this channel.", ephemeral=True)
        return

    # Add general channel check
    if guild_id == CAPRICA_SERVER_ID and interaction.channel_id == 1189630582280441997 and not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("I only respond to my owner in this channel.", ephemeral=True)
        return
"""

analyze_start = """@bot.tree.command(name="analyze", description="Run a deep analysis on a topic using the wiki or databases.")
async def analyze_command(interaction: discord.Interaction, query: str):
    if is_banned(interaction.user.id):
        await interaction.response.send_message("You are not authorized to use this bot.", ephemeral=True)
        return

    guild_id = interaction.guild.id if interaction.guild else None
    if guild_id != TEST_SERVER_ID and (guild_id != CAPRICA_SERVER_ID or interaction.channel_id not in ALLOWED_CAPRICA_CHANNELS):
        await interaction.response.send_message("I am currently restricted from this channel.", ephemeral=True)
        return

    # Add general channel check
    if guild_id == CAPRICA_SERVER_ID and interaction.channel_id == 1189630582280441997 and not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("I only respond to my owner in this channel.", ephemeral=True)
        return
"""

import re
code = re.sub(r'@bot\.tree\.command\(name="think".*?return\n', think_start, code, flags=re.DOTALL)
code = re.sub(r'@bot\.tree\.command\(name="analyze".*?return\n', analyze_start, code, flags=re.DOTALL)

with open("src/bot.py", "w") as f:
    f.write(code)
