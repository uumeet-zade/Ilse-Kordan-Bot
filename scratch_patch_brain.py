import re

with open('src/brain.py', 'r') as f:
    content = f.read()

# For search_wiki
content = re.sub(r'result = search_wiki\(args\.get\("query", ""\)\)', r'result = await asyncio.to_thread(search_wiki, args.get("query", ""))', content)
# For get_ilse_opinion
content = re.sub(r'result = get_ilse_opinion\(args\.get\("entity_name", ""\)\)', r'result = await asyncio.to_thread(get_ilse_opinion, args.get("entity_name", ""))', content)
# For search_bills
content = re.sub(r'result = search_bills\(args\.get\("query", ""\)\)', r'result = await asyncio.to_thread(search_bills, args.get("query", ""))', content)
# For search_regional_bills
content = re.sub(r'result = search_regional_bills\(args\.get\("region", ""\), args\.get\("query", ""\)\)', r'result = await asyncio.to_thread(search_regional_bills, args.get("region", ""), args.get("query", ""))', content)
# For search_lore
content = re.sub(r'result = search_lore\(args\.get\("query", ""\), args\.get\("channel_name", ""\)\)', r'result = await asyncio.to_thread(search_lore, args.get("query", ""), args.get("channel_name", ""))', content)
# For read_google_doc
content = re.sub(r'result = read_google_doc\(args\.get\("url", ""\)\)', r'result = await asyncio.to_thread(read_google_doc, args.get("url", ""))', content)
# For read_google_sheet
content = re.sub(r'result = read_google_sheet\(args\.get\("url", ""\)\)', r'result = await asyncio.to_thread(read_google_sheet, args.get("url", ""))', content)
# For note_bill_opinion
content = re.sub(r'result = note_bill_opinion\(args\.get\("title", ""\), args\.get\("liked", ""\), args\.get\("disliked", ""\)\)', r'result = await asyncio.to_thread(note_bill_opinion, args.get("title", ""), args.get("liked", ""), args.get("disliked", ""))', content)
# For create_google_doc
content = re.sub(r'result = create_google_doc\(args\.get\("title", ""\), args\.get\("content", ""\)\)', r'result = await asyncio.to_thread(create_google_doc, args.get("title", ""), args.get("content", ""))', content)


with open('src/brain.py', 'w') as f:
    f.write(content)
