"""Проверка собранного PDF: внутренние ссылки, закладки, страницы билетов.

Печатает сводку и пишет pages.json: {"t1": 2, ..., "formulas": N} — номера
страниц (с 1), на которые ведут ссылки оглавления.
"""
import json
import re
import sys
from pypdf import PdfReader

path = sys.argv[1] if len(sys.argv) > 1 else 'exam.pdf'
out = sys.argv[2] if len(sys.argv) > 2 else 'pages.json'
r = PdfReader(path)
print('страниц:', len(r.pages))

page_index = {p.indirect_reference.idnum: i for i, p in enumerate(r.pages)}
named = r.named_destinations
pages = {}
for name, dest in named.items():
    try:
        pages[name] = r.get_destination_page_number(dest) + 1
    except Exception as e:  # noqa: BLE001
        print('не удалось разрешить', name, e)


def resolve(annot):
    """Номер страницы (с 1), на которую ведёт ссылка-аннотация, или None."""
    if '/Dest' in annot:
        d = annot['/Dest']
    elif '/A' in annot and annot['/A'].get('/S') == '/GoTo':
        d = annot['/A']['/D']
    else:
        return None
    if isinstance(d, str) or hasattr(d, 'decode'):
        dd = named.get(str(d))
        return pages.get(str(d)) if dd is not None else None
    d = d.get_object() if hasattr(d, 'get_object') else d
    return page_index.get(d[0].idnum, -2) + 1


# Ссылки первой страницы (оглавление) в порядке появления.
first = r.pages[0]
links = []
for a in first.get('/Annots', []) or []:
    a = a.get_object()
    if a.get('/Subtype') != '/Link':
        continue
    links.append(resolve(a))
print('ссылок на странице 1:', len(links), '->', links)

# Все внутренние ссылки документа должны куда-то вести.
bad = 0
total = 0
for i, p in enumerate(r.pages):
    for a in p.get('/Annots', []) or []:
        a = a.get_object()
        if a.get('/Subtype') != '/Link':
            continue
        total += 1
        if '/A' in a and a['/A'].get('/S') == '/URI':
            continue
        if resolve(a) in (None, -1):
            bad += 1
            print('битая ссылка на странице', i + 1)
print('внутренних ссылок всего:', total, 'битых:', bad)

# Chromium пишет явные /Dest без имён, поэтому номера страниц берём из
# ссылок оглавления (в порядке DOM: t1..t19, затем formulas) и сверяем с текстом.
keys = [f't{i}' for i in range(1, 20)] + ['formulas']
want = {}
problems = 0
for key, pg in zip(keys, links):
    want[key] = pg
    text = re.sub(r'\s+', ' ', r.pages[pg - 1].extract_text() or '')
    marker = 'Приложение' if key == 'formulas' else f'Билет {key[1:]}.'
    if marker not in text:
        problems += 1
        print('!! на странице', pg, 'нет заголовка', marker)
if len(links) != len(keys):
    problems += 1
    print('!! ожидалось', len(keys), 'ссылок в оглавлении, найдено', len(links))
print('страницы билетов:', json.dumps(want, ensure_ascii=False))
print('закладок верхнего уровня:', len(r.outline))
print('проблем:', problems)
json.dump(want, open(out, 'w'), ensure_ascii=False, indent=1)
