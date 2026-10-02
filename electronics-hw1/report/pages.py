"""Номера страниц заголовков по PDF (для кэша оглавления в docx)."""
import json
import re
import subprocess
import sys

pdf = sys.argv[1]
heads = json.load(open('headings.json'))
npages = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout).group(1))
norm = lambda s: re.sub(r'\s+', ' ', s).strip()
texts = []
for p in range(1, npages + 1):
    t = subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), '-layout', pdf, '-'], capture_output=True, text=True).stdout
    texts.append([norm(l) for l in t.splitlines() if l.strip()])
# пропускаем титульный лист и оглавление: ищем первый заголовок после страницы «СОДЕРЖАНИЕ»
start = next(i for i, lines in enumerate(texts) if any(l == 'СОДЕРЖАНИЕ' for l in lines)) + 1
pages = {}
cur = start
for h in heads:
    key = norm(re.sub(r'_\{([^}]*)\}|\^\{([^}]*)\}', lambda m: m.group(1) or m.group(2), h['text']))
    key = key[:45]
    found = None
    for i in range(cur, npages):
        if any(l.startswith(key) for l in texts[i]):
            found = i
            break
    if found is None:
        # заголовок мог перенестись на две строки
        for i in range(cur, npages):
            if key[:25] in ' '.join(texts[i]):
                found = i
                break
    if found is None:
        print('NOT FOUND', h['text'])
        continue
    pages[h['id']] = found + 1
    cur = found
json.dump(pages, open('pages.json', 'w'), indent=1)
print(pages)
