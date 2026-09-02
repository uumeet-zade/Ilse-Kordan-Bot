from wiki import search_live_wiki, fetch_page_content
titles = search_live_wiki('List of Prime Ministers of Caprica')
for title in titles:
    content, _ = fetch_page_content(title)
    if content:
        print(f"Match: {title}")
        print(content[:500])
        print("\n\n" + "-"*50 + "\n\n")
