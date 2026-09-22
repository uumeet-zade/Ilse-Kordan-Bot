import json, urllib.request
with urllib.request.urlopen("https://caprica.miraheze.org/w/api.php?action=parse&page=Main_Page&format=json&prop=text") as response:
    data = json.loads(response.read().decode())
    text = data['parse']['text']['*']
    import re
    matches = re.finditer(r'<li.*?>.*?<a[^>]*>(.*?)</a>.*?</li>', text)
    for m in matches:
        if "Act" in m.group(0) or "YAY" in m.group(0):
            print(m.group(0))
