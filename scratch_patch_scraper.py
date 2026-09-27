import re

with open('src/auto_scraper.py', 'r') as f:
    content = f.read()

# Replace read_google_doc_sync with await asyncio.to_thread(read_google_doc_sync, doc_link)
content = re.sub(r'read_google_doc_sync\(doc_link\)', r'await asyncio.to_thread(read_google_doc_sync, doc_link)', content)

# Replace extract_main_goal_llm(doc_text, title) with await asyncio.to_thread(extract_main_goal_llm, doc_text, title)
content = re.sub(r'extract_main_goal_llm\(doc_text, title\)', r'await asyncio.to_thread(extract_main_goal_llm, doc_text, title)', content)

with open('src/auto_scraper.py', 'w') as f:
    f.write(content)
