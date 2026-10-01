// Сборка PDF «Электроника, модуль 4: ответы на экзаменационные билеты».
// content/tNN.md  -> HTML (markdown-it + KaTeX) -> PDF (Chromium через Playwright).
// Использование: node build.js [pages.json]
//   pages.json — номера страниц билетов, найденные после первого прохода
//   (их выводит check_pdf.py); без него оглавление собирается без номеров.
const fs = require('fs');
const path = require('path');
const katex = require('katex');
const MarkdownIt = require('markdown-it');
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  ({ chromium } = require('/opt/node22/lib/node_modules/playwright'));
}

const ROOT = __dirname;
const OUT_HTML = path.join(ROOT, 'exam.html');
const OUT_PDF = path.join(ROOT, 'exam.pdf');
const md = new MarkdownIt({ html: true, typographer: false });

const TICKETS = [
  [1, 'Логические (цифровые) электронные схемы. Определение, классификация. Современные тенденции развития.', 'Определение, классификация, тенденции развития'],
  [2, 'Логические (цифровые) электронные схемы. Переход от информационного к электрическому уровню описания логического блока.', 'Переход от информационного к электрическому уровню'],
  [3, 'Логические (цифровые) электронные схемы. Сравнение характеристик различных семейств.', 'Сравнение семейств логики'],
  [4, 'Логические (цифровые) электронные схемы. Инвертор на n-МОП-технологии. Вывод передаточной характеристики.', 'n-МОП инвертор: вывод ПХ'],
  [5, 'Логические (цифровые) электронные схемы. Инвертор на КМОП-технологии. Вывод передаточной характеристики.', 'КМОП-инвертор: вывод ПХ'],
  [6, 'Логические (цифровые) электронные схемы. Инвертор на КМОП-технологии. Физическая структура. Топология. Передаточная характеристика.', 'КМОП-инвертор: структура, топология, ПХ'],
  [7, 'Логические (цифровые) электронные схемы. КМОП-логика. КМОП схема И-НЕ. Характеристики и принцип работы.', 'КМОП схема И-НЕ'],
  [8, 'Логические (цифровые) электронные схемы. КМОП-логика. КМОП схема ИЛИ-НЕ. Характеристики и принцип работы.', 'КМОП схема ИЛИ-НЕ'],
  [9, 'Логические (цифровые) электронные схемы. КМОП-логика. Структура и условия комплементарности.', 'Структура КМОП, условия комплементарности'],
  [10, 'Логические (цифровые) электронные схемы. КМОП-логика. Простейший способ построения комбинационной схемы.', 'Построение комбинационной КМОП-схемы'],
  [11, 'Логические (цифровые) электронные схемы. КМОП-логика. Особенности физической реализации.', 'Физическая реализация КМОП'],
  [12, 'Логические (цифровые) электронные схемы. Основные характеристики и параметры логических ячеек. Передаточная и переходная характеристики.', 'Характеристики и параметры: ПХ и переходная'],
  [13, 'Логические (цифровые) электронные схемы. Основные статические параметры. Способ определения по электрическим характеристикам.', 'Статические параметры: способ определения'],
  [14, 'Логические (цифровые) электронные схемы. Основные статические параметры. Помехоустойчивость.', 'Помехоустойчивость'],
  [15, 'Логические (цифровые) электронные схемы. Основные статические параметры. Статическая мощность потребления.', 'Статическая мощность потребления'],
  [16, 'Логические (цифровые) электронные схемы. Основные динамические параметры. Способ определения по электрическим характеристикам.', 'Динамические параметры: способ определения'],
  [17, 'Логические (цифровые) электронные схемы. Основные динамические параметры. Влияние нагрузки на процесс переключения.', 'Влияние нагрузки на переключение'],
  [18, 'Логические (цифровые) электронные схемы. Основные динамические параметры. Динамическая мощность потребления.', 'Динамическая мощность потребления'],
  [19, 'Логические (цифровые) электронные схемы. Основные динамические параметры. Энергия переключения.', 'Энергия переключения'],
];

// Кириллица внутри формул набирается прямым шрифтом через \text{…}.
function wrapCyrillic(tex) {
  return tex.replace(/[А-Яа-яЁё]+/g, (m) => `\\text{${m}}`);
}

function renderMath(tex, display) {
  try {
    return katex.renderToString(wrapCyrillic(tex), {
      displayMode: display, throwOnError: true, strict: 'ignore', output: 'html',
    });
  } catch (e) {
    throw new Error(`KaTeX: ${e.message}\n  в формуле: ${tex}`);
  }
}

// ::fig ID | подпись | источник [| ширина %]
function expandFigures(src, ticket) {
  let k = 0;
  // [ \t] вместо \s: перевод строки после директивы должен остаться, иначе
  // HTML-блок рисунка «склеится» со следующим абзацем.
  return src.replace(/^::fig[ \t]+(\S+)[ \t]*\|[ \t]*(.+?)[ \t]*\|[ \t]*(.+?)(?:[ \t]*\|[ \t]*(\d+))?[ \t]*$/gm,
    (_, ids, caption, source, width) => {
      const list = ids.split(',');
      for (const id of list) {
        if (!fs.existsSync(path.join(ROOT, 'img', `${id}.jpg`))) throw new Error(`нет рисунка ${id}`);
      }
      k += 1;
      const w = ` style="width:${width || (list.length > 1 ? 100 : 72)}%"`;
      const imgs = list.map((id) => `<img src="img/${id}.jpg" alt="${id}">`).join('');
      const cls = list.length > 1 ? 'fig multi' : 'fig';
      return `<figure class="${cls}"${w}><div class="imgs">${imgs}</div>` +
        `<figcaption><b>Рис. ${ticket}.${k}.</b> ${caption} <span class="src">[${source}]</span></figcaption></figure>`;
    });
}

function renderMarkdown(src, ticket) {
  const maths = [];
  let text = expandFigures(src, ticket);
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, t) => { maths.push([t, true]); return `MATHPH${maths.length - 1}X`; });
  text = text.replace(/\$([^$\n]+?)\$/g, (_, t) => { maths.push([t, false]); return `MATHPH${maths.length - 1}X`; });
  let html = md.render(text);
  html = html.replace(/<p>MATHPH(\d+)X<\/p>/g, (_, i) => renderMath(...maths[+i]));
  html = html.replace(/MATHPH(\d+)X/g, (_, i) => renderMath(...maths[+i]));
  if (html.includes('$')) console.warn(`[билет ${ticket}] остался символ $ — проверьте разметку формул`);
  return html;
}

function navPage(pages) {
  const items = TICKETS.map(([n, , short]) => {
    const pg = pages && pages[`t${n}`] ? `<span class="pg">стр. ${pages[`t${n}`]}</span>` : '<span class="pg"></span>';
    return `<a class="nav-item" href="#t${n}"><span class="num">${n}</span><span class="ttl">${short}</span>${pg}</a>`;
  }).join('\n');
  const fpg = pages && pages.formulas ? `<span class="pg">стр. ${pages.formulas}</span>` : '<span class="pg"></span>';
  return `<section id="nav" class="nav">
<div class="cover">
  <div class="cover-kicker">Электроника · 2-й курс · поток БИТ · модуль 4</div>
  <div class="cover-title">Логические (цифровые) электронные схемы</div>
  <div class="cover-sub">Развёрнутые ответы на вопросы к экзамену — по материалам лекций Л.&nbsp;М.&nbsp;Самбурского (МИЭМ НИУ ВШЭ)</div>
</div>
<h1 class="nav-title">Оглавление</h1>
<div class="nav-hint">Нажмите на билет, чтобы перейти к ответу. В начале и в конце каждого ответа есть ссылка «к оглавлению»; закладки PDF повторяют структуру ответов.</div>
<div class="nav-grid">
${items}
</div>
<a class="nav-extra" href="#formulas"><span class="num">Σ</span><span class="ttl">Сводка основных формул</span>${fpg}</a>
<div class="legend">
  <b>Условные обозначения.</b> [Л16, сл. 9] — лекция 16, слайд 9; рисунки взяты со слайдов лекций.
  ПХ — передаточная характеристика; PU/PD — цепи, подтягивающие выход к питанию/к земле.
  <span class="legend-note">Блоки «Комментарий»</span> содержат пояснения и промежуточные выкладки, выведенные из формул лекций
  (на слайдах в готовом виде их нет); <span class="legend-typo">«Замечание к слайду»</span> — места, где на слайде, по-видимому, опечатка;
  всё остальное — изложение материала слайдов.
</div>
</section>`;
}

function ticketSection([n, title]) {
  const file = path.join(ROOT, 'content', `t${String(n).padStart(2, '0')}.md`);
  const body = fs.existsSync(file) ? renderMarkdown(fs.readFileSync(file, 'utf8'), n) : '<p><i>(ответ готовится)</i></p>';
  const next = n < TICKETS.length ? ` · <a href="#t${n + 1}">билет ${n + 1} →</a>` : '';
  // Общее начало всех вопросов выносим в «шапку», чтобы заголовок (и закладка PDF)
  // начинался с номера билета; вместе они дают полный текст вопроса из программы.
  const PREFIX = 'Логические (цифровые) электронные схемы. ';
  if (!title.startsWith(PREFIX)) throw new Error(`неожиданный заголовок билета ${n}`);
  return `<section class="ticket" id="t${n}">
<div class="t-head"><div class="t-kicker">${PREFIX.trim()}</div><a class="back" href="#nav">↑ к оглавлению</a></div>
<h1 class="t-title"><span class="t-num">Билет ${n}.</span> ${title.slice(PREFIX.length)}</h1>
${body}
<div class="t-foot"><a href="#nav">↑ к оглавлению</a>${next}</div>
</section>`;
}

function formulasSection() {
  const file = path.join(ROOT, 'content', 'formulas.md');
  if (!fs.existsSync(file)) return '';
  return `<section class="ticket" id="formulas">
<div class="t-head"><div class="t-kicker">Приложение</div><a class="back" href="#nav">↑ к оглавлению</a></div>
<h1 class="t-title"><span class="t-num">Приложение.</span> Сводка основных формул</h1>
${renderMarkdown(fs.readFileSync(file, 'utf8'), 'Ф')}
<div class="t-foot"><a href="#nav">↑ к оглавлению</a></div>
</section>`;
}

function buildHtml(pages) {
  const fontCss = ['pt-serif/400.css', 'pt-serif/400-italic.css', 'pt-serif/700.css', 'pt-serif/700-italic.css',
    'pt-sans/400.css', 'pt-sans/700.css']
    .map((f) => `<link rel="stylesheet" href="node_modules/@fontsource/${f}">`).join('\n');
  return `<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>Электроника — модуль 4: ответы на билеты</title>
${fontCss}
<link rel="stylesheet" href="node_modules/katex/dist/katex.min.css">
<link rel="stylesheet" href="style.css">
</head><body>
${navPage(pages)}
${TICKETS.map(ticketSection).join('\n')}
${formulasSection()}
</body></html>`;
}

async function main() {
  const pagesFile = process.argv[2];
  const pages = pagesFile && fs.existsSync(pagesFile) ? JSON.parse(fs.readFileSync(pagesFile, 'utf8')) : null;
  fs.writeFileSync(OUT_HTML, buildHtml(pages));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + OUT_HTML, { waitUntil: 'load' });
  await page.evaluate(async () => { await document.fonts.ready; });
  const broken = await page.evaluate(() => [...document.images].filter((i) => !i.complete || !i.naturalWidth).map((i) => i.src));
  if (broken.length) throw new Error('не загрузились рисунки: ' + broken.join(', '));
  await page.pdf({
    path: OUT_PDF, format: 'A4', printBackground: true, outline: true, tagged: true,
    margin: { top: '14mm', bottom: '15mm', left: '15mm', right: '15mm' },
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: `<div style="width:100%;font-family:'DejaVu Sans',sans-serif;font-size:7.5px;color:#7a7f95;padding:0 15mm;display:flex;justify-content:space-between;">
      <span>Электроника · модуль 4 · ответы на экзаменационные билеты</span>
      <span>стр. <span class="pageNumber"></span> из <span class="totalPages"></span></span></div>`,
  });
  await browser.close();
  console.log('PDF:', OUT_PDF);
}

main().catch((e) => { console.error(e); process.exit(1); });
