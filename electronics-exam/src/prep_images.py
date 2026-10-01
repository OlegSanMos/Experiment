"""Вырезает иллюстрации для PDF из слайдов лекций.

Использование: python3 prep_images.py <папка с PDF лекций>

Страницы рендерятся в 300 dpi (pdftoppm из poppler-utils); координаты
вырезок заданы в пикселях рендера 200 dpi и масштабируются.  'full' —
слайд целиком (обрезаются белые поля страницы).  Результат: img/<id>.jpg.
"""
import glob
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LECTURES = sys.argv[1] if len(sys.argv) > 1 else '.'


def lecture_pdf(num):
    """PDF лекции по номеру: имя содержит «Lecture_NN» или «Lecture NN»."""
    for path in sorted(glob.glob(os.path.join(LECTURES, '*.pdf'))):
        name = os.path.basename(path).replace(' ', '_')
        if re.search(rf'Lecture_{num:02d}\b', name) or re.search(rf'Lecture_{num:02d}[-_]', name):
            return path
    sys.exit(f'не найден PDF лекции {num} в {LECTURES}')


PDF = {f'L{n:02d}': n for n in (1, 3, 8, 9, 15, 16, 17, 18, 19)}
# id: (lecture, pdf page, crop)
MANIFEST = {
    'L01s05': ('L01', 5, 'full'),
    'L01s19': ('L01', 18, 'full'),
    'L01s20': ('L01', 19, 'full'),
    'L01s21': ('L01', 20, 'full'),
    'L01s23': ('L01', 22, 'full'),
    'L03s13': ('L03', 13, (66, 401, 921, 1007)),
    'L08s06': ('L08', 6, (44, 298, 1941, 743)),
    'L08s11': ('L08', 11, 'full'),
    'L08s15': ('L08', 15, (195, 298, 1859, 1151)),
    'L08s16': ('L08', 16, 'full'),
    'L09s08': ('L09', 8, 'full'),
    'L09s14': ('L09', 14, 'full'),
    'L09s21': ('L09', 21, 'full'),
    'L15s03': ('L15', 3, 'full'),
    'L16s04': ('L16', 4, (968, 660, 1899, 1171)),
    'L16s07': ('L16', 7, 'full'),
    'L16s08': ('L16', 8, 'full'),
    'L16s09': ('L16', 9, 'full'),
    'L16s10': ('L16', 10, 'full'),
    'L16s10cmos': ('L16', 10, (1490, 390, 1968, 846)),
    'L16s12': ('L16', 12, 'full'),
    'L16s13': ('L16', 13, 'full'),
    'L16s14': ('L16', 14, (17, 376, 1954, 1013)),
    'L16s15': ('L16', 15, (217, 292, 1669, 1124)),
    'L16s16': ('L16', 16, 'full'),
    'L16s17': ('L16', 17, 'full'),
    'L17s05': ('L17', 5, 'full'),
    'L17s06': ('L17', 6, 'full'),
    'L17s07': ('L17', 7, 'full'),
    'L17s08': ('L17', 8, 'full'),
    'L18s05': ('L18', 5, 'full'),
    'L18s06': ('L18', 6, 'full'),
    'L18s07': ('L18', 7, 'full'),
    'L18s08': ('L18', 8, 'full'),
    'L18s09': ('L18', 9, 'full'),
    'L18s10': ('L18', 10, 'full'),
    'L18s11': ('L18', 11, 'full'),
    'L18s12': ('L18', 12, 'full'),
    'L18s13': ('L18', 13, 'full'),
    'L18s14': ('L18', 14, (331, 437, 2009, 1256)),
    'L18s15': ('L18', 15, (331, 437, 2009, 1256)),
    'L18s16': ('L18', 16, (311, 456, 1989, 1275)),
    'L18s17': ('L18', 17, (311, 456, 1989, 1275)),
    'L18s18': ('L18', 18, (116, 417, 2184, 1284)),
    'L18s19': ('L18', 19, 'full'),
    'L18s20': ('L18', 20, 'full'),
    'L19s10': ('L19', 10, 'full'),
    'L19s11': ('L19', 11, 'full'),
    'L19s15': ('L19', 15, 'full'),
}
RENDER = os.path.join(HERE, 'slides300')
OUT = os.path.join(HERE, 'img')
MAXW = 1700
os.makedirs(RENDER, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

def page_png(lec, page):
    path = f'{RENDER}/{lec}-p{page:02d}.png'
    if not os.path.exists(path):
        stem = path[:-4]
        subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', '300',
                        '-png', '-singlefile', lecture_pdf(PDF[lec]), stem], check=True)
    return path

def slide_box(im):
    a = np.asarray(im.convert('RGB')).astype(int)
    mask = (a < 200).any(axis=2)
    rows = np.where(mask.mean(axis=1) > 0.5)[0]
    cols = np.where(mask.mean(axis=0) > 0.5)[0]
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1

for fid, (lec, page, crop) in MANIFEST.items():
    im = Image.open(page_png(lec, page)).convert('RGB')
    if crop == 'full':
        box = slide_box(im)
    else:
        box = tuple(int(round(v * 1.5)) for v in crop)
    fig = im.crop(box)
    if fig.width > MAXW:
        fig = fig.resize((MAXW, round(fig.height * MAXW / fig.width)), Image.LANCZOS)
    fig.save(f'{OUT}/{fid}.jpg', quality=86, optimize=True, progressive=True)
    print(f'{fid:12s} {lec} p{page:<3d} box={box} -> {fig.size}')
