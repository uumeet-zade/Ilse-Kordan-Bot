import os

with open("brain.py", "r") as f:
    content = f.read()

content = content.replace(
    'prompt_text += "\\n\\nCRITICAL: Before writing your final response to the user, you MUST write out your internal reasoning wrapped precisely in <THOUGHT> and </THOUGHT> tags. Do this at the very beginning of your response."',
    'prompt_text += "\\n\\nCRITICAL: Before writing your final response to the user, you MUST write out your internal reasoning wrapped precisely in <THOUGHT> and </THOUGHT> tags. Do this at the very beginning of your response. When asked to list Prime Ministers, ALWAYS read the full list, pay close attention to the dates to determine who the most recent ones are, and NEVER invent names or make assumptions without verifying the full table data first."'
)

with open("brain.py", "w") as f:
    f.write(content)

print("patched")
