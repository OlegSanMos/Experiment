"""Постобработка docx: уникальные id закладок (docx-js даёт всем закладкам id=1)."""
import re
import sys
import zipfile

src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else src
zin = zipfile.ZipFile(src)
items = [(i, zin.read(i.filename)) for i in zin.infolist()]
zin.close()
out = []
for info, data in items:
    if info.filename == 'word/document.xml':
        xml = data.decode('utf-8')
        counter = [0]
        stack = []

        def repl(m):
            tag = m.group(0)
            if tag.startswith('<w:bookmarkStart'):
                counter[0] += 1
                stack.append(counter[0])
                return re.sub(r'w:id="\d+"', f'w:id="{counter[0]}"', tag)
            bid = stack.pop() if stack else counter[0]
            return re.sub(r'w:id="\d+"', f'w:id="{bid}"', tag)

        xml = re.sub(r'<w:bookmark(?:Start|End)\b[^>]*/>', repl, xml)
        data = xml.encode('utf-8')
    out.append((info, data))
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
    for info, data in out:
        z.writestr(info, data)
print('bookmarks renumbered:', dst)
