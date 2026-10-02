#!/bin/bash
# Сборка отчёта: docx -> pdf (LibreOffice) -> номера страниц для оглавления -> повторная сборка,
# пока номера страниц не перестанут меняться. Результат: report.docx, report.pdf.
set -e
cd "$(dirname "$0")"
WRAP=/root/.claude/skills/synced/5f06d5b2-47ba-47a7-9dee-6444407a56be_e5711885-07b2-4f89-9d87-61b472c57324/docx/scripts/office/soffice.py
if [ -f "$WRAP" ]; then SOFFICE="python3 $WRAP"; else SOFFICE=soffice; fi
export NODE_PATH=${NODE_PATH:-/opt/node-tools/node_modules}
for i in 1 2 3; do
  node build.js report.docx > /dev/null
  python3 fixdocx.py report.docx > /dev/null
  rm -f report.pdf
  $SOFFICE --headless --convert-to pdf report.docx > /dev/null 2>&1
  cp -f pages.json pages_prev.json 2>/dev/null || echo '{}' > pages_prev.json
  python3 pages.py report.pdf > /dev/null
  if cmp -s pages.json pages_prev.json; then echo "pages stable after pass $i"; break; fi
done
pdfinfo report.pdf | grep Pages
