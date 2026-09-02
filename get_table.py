from wiki import fetch_page_content
content, _ = fetch_page_content('Prime Minister of Caprica')
if content:
    lines = content.split('\n')
    start_idx = 0
    end_idx = 0
    for i, line in enumerate(lines):
        if 'Calixte Edinburgh' in line or 'Patrick Cutter' in line or 'Mandy Trottier' in line:
            start_idx = max(0, i - 15)
            break
            
    if start_idx:
        for i in range(start_idx, len(lines)):
            if 'Adriana Flash' in lines[i]:
                end_idx = min(len(lines), i + 20)
                break
                
    if start_idx and end_idx:
        print('\n'.join(lines[start_idx:end_idx]))
