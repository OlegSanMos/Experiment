#!/usr/bin/env bash
# Сборка до стабилизации номеров страниц в оглавлении (обычно 2 прохода).
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
rm -f pages.json
node build.js >/dev/null
$PY check_pdf.py exam.pdf pages.json >/dev/null
for i in 1 2 3; do
  node build.js pages.json >/dev/null
  $PY check_pdf.py exam.pdf pages_new.json > check.log
  if cmp -s pages.json pages_new.json; then
    cat check.log
    echo "страниц в PDF: $(pdfinfo exam.pdf | awk '/^Pages/{print $2}')"
    exit 0
  fi
  mv pages_new.json pages.json
done
echo "номера страниц не стабилизировались" >&2
exit 1
