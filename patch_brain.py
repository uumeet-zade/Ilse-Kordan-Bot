import os

with open("brain.py", "r") as f:
    content = f.read()

# Replace imports
content = content.replace("import google.generativeai as genai\nfrom google.api_core.exceptions import ResourceExhausted, InternalServerError", "from mistralai import Mistral\nimport json")

# Remove genai.configure
content = content.replace('genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))', '')

# Replace MODEL_FALLBACKS
content = content.replace("""MODEL_FALLBACKS = [
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-3.5-flash-lite',
    'gemini-3.1-flash-lite'
]""", """MODEL_FALLBACKS = [
    'mistral-large-latest',
    'pixtral-large-latest',
    'mistral-medium-latest',
    'mistral-small-latest',
    'pixtral-12b-2409'
]""")

# Define mistral_tools JSON array before generate_response
mistral_tools_def = '''
mistral_tools = [
    {
        "type": "function",
        "function": {
            "name": "search_wiki",
            "description": "Searches the live Caprica Miraheze wiki for lore, people, governments, and bills. Extract ONLY the core, full name from the user's prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ilse_opinion",
            "description": "Fetches Ilse Kordan's pre-computed political opinion on a specific person, bill, or entity from the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string"}
                },
                "required": ["entity_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_bills",
            "description": "Searches the database for Caprican bills by title or proposer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_regional_bills",
            "description": "Searches the database for Regional Bills based on Region name and/or Bill Title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {"type": "string"},
                    "query": {"type": "string"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_lore",
            "description": "Searches the database of historical discord channels based on keywords.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_google_doc",
            "description": "Extracts text from a public Google Doc link to read a proposed bill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "note_bill_opinion",
            "description": "Records Ilse Kordan's dynamic opinion on a bill to the database and the public opinions document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "liked": {"type": "string"},
                    "disliked": {"type": "string"}
                },
                "required": ["title", "liked", "disliked"]
            }
        }
    }
]

'''

# Extract everything up to generate_response
gen_idx = content.find('async def generate_response')
part1 = content[:gen_idx]

part2 = '''async def generate_response(message_content, chat_history, is_test_server=False, current_user="Unknown User", image_data=None):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d")
    prompt_text = f"System Context: Today's real-world date is {current_time}.\\n\\nRecent Chat History for context:\\n{chat_history}\\n\\nCurrent User talking to you: {current_user}\\nTheir Question/Command:\\n{message_content}"
    prompt_text += "\\n\\nCRITICAL: Before writing your final response to the user, you MUST write out your internal reasoning wrapped precisely in <THOUGHT> and </THOUGHT> tags. Do this at the very beginning of your response."
    
    sys_prompt = SYSTEM_PROMPT
    if is_test_server:
        sys_prompt = "[ENVIRONMENT: TEST SERVER. This is a strictly classified OOC sandbox. You have been physically disconnected from the main database's write-access. Everything discussed here cannot be leaked. If the user asks about confidentiality, assure them you are physically incapable of leaking test data to the main server.]\\n\\n" + sys_prompt
        
    messages = [
        {"role": "system", "content": sys_prompt}
    ]
    
    user_content = []
    if image_data:
        user_content.append({"type": "image_url", "image_url": image_data})
    user_content.append({"type": "text", "text": prompt_text})
    
    messages.append({"role": "user", "content": user_content})

    disabled_models = load_disabled_models()
    
    client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

    for model_name in MODEL_FALLBACKS:
        if model_name in disabled_models:
            if time.time() < disabled_models[model_name]:
                print(f"[INFO] Skipping {model_name} because it is temporarily disabled.")
                continue
            else:
                del disabled_models[model_name]
                save_disabled_models(disabled_models)
                
        try:
            current_messages = list(messages)
            
            # Mistral chat loop for tools
            while True:
                response = await asyncio.to_thread(
                    client.chat.complete,
                    model=model_name,
                    messages=current_messages,
                    tools=mistral_tools,
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                
                if response_message.tool_calls:
                    # Append assistant's tool call request
                    current_messages.append(response_message)
                    
                    for tool_call in response_message.tool_calls:
                        func_name = tool_call.function.name
                        try:
                            args = json.loads(tool_call.function.arguments)
                        except:
                            args = {}
                            
                        result = ""
                        if func_name == "search_wiki":
                            result = search_wiki(args.get("query", ""))
                        elif func_name == "get_ilse_opinion":
                            result = get_ilse_opinion(args.get("entity_name", ""))
                        elif func_name == "search_bills":
                            result = search_bills(args.get("query", ""))
                        elif func_name == "search_regional_bills":
                            result = search_regional_bills(args.get("region", ""), args.get("query", ""))
                        elif func_name == "search_lore":
                            result = search_lore(args.get("query", ""))
                        elif func_name == "read_google_doc":
                            result = read_google_doc(args.get("url", ""))
                        elif func_name == "note_bill_opinion" and not is_test_server:
                            result = note_bill_opinion(args.get("title", ""), args.get("liked", ""), args.get("disliked", ""))
                        else:
                            result = f"Error: Tool {func_name} not found or not permitted in this environment."
                            
                        # Append the tool result
                        current_messages.append({
                            "role": "tool",
                            "name": func_name,
                            "content": result,
                            "tool_call_id": tool_call.id
                        })
                else:
                    return response_message.content
                    
        except Exception as e:
            print(f"[ERROR] LLM Error with {model_name}: {e}")
            disabled_models[model_name] = time.time() + (2 * 60 * 60)
            save_disabled_models(disabled_models)
            print(f"[INFO] {model_name} has been temporarily disabled for 2 hours.")
            continue
            
    return "<API_EXHAUSTED>"
'''

with open("brain.py", "w") as f:
    f.write(part1 + mistral_tools_def + part2)

print("brain.py has been successfully patched!")
