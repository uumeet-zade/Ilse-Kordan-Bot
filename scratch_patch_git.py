import re

with open('src/auto_scraper.py', 'r') as f:
    content = f.read()

# Replace subprocess.run(...) with await asyncio.to_thread(subprocess.run, ...)
content = re.sub(r'subprocess\.run\(\[(.*?)\], check=True, cwd=BASE_DIR\)',
                 r'await asyncio.to_thread(subprocess.run, [\1], check=True, cwd=BASE_DIR)',
                 content)

with open('src/auto_scraper.py', 'w') as f:
    f.write(content)
