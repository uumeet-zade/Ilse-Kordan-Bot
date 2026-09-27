with open("src/bot.py", "r") as f:
    content = f.read()

injection = """@bot.tree.command(name="shutdown", description="[OWNER ONLY] Shut down the bot completely.")
async def shutdown_command(interaction: discord.Interaction):
    if not is_owner_or_authorized(interaction.user):
        await interaction.response.send_message("You do not have permission to shut me down.", ephemeral=True)
        return
        
    await interaction.response.send_message("Shutting down... Goodbye!", ephemeral=True)
    print(f"[INFO] Shutdown command received from {interaction.user.name}.")
    import sys
    await bot.close()
    sys.exit(0)

"""

new_content = content.replace("async def start_web_server():", injection + "async def start_web_server():")

with open("src/bot.py", "w") as f:
    f.write(new_content)
