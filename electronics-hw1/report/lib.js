// Вспомогательные функции сборки отчёта (docx-js): разметка текста, нумерация рисунков,
// таблиц, листингов и формул, рендеринг блоков.
const fs = require('fs');
const path = require('path');
const D = require('docx');
const {
  Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, BorderStyle,
  ShadingType, HeadingLevel, TabStopType, Bookmark, VerticalAlign, LevelFormat,
} = D;

const TW = 9638;            // ширина текста, twip (21 − 3 − 1 = 17 см)
const CM = 567;             // twip в 1 см
const FONT = 'Times New Roman';
const MONO = 'Courier New';

// ---------- числа ----------
function n(x, d) {
  const s = Number(x).toFixed(d).replace('.', ',');
  return s.startsWith('-') ? '−' + s.slice(1) : s;
}
function sgn(x, d) {            // со знаком: +4,8 / −0,4
  return (x >= 0 ? '+' : '') + n(x, d);
}
function dev(x, ref, d = 1) {   // отклонение в процентах
  return sgn((x / ref - 1) * 100, d) + ' %';
}

// ---------- разметка: _{нижний}, ^{верхний}, <i>курсив</i>, <b>жирный</b> ----------
const NBSP = ' ';
const UNITS = 'В|мВ|кВ|А|мА|мкА|пА|Ом|кОм|мОм|Ф|мкФ|мФ|пФ|нс|мкс|мс|с|Гц|мкГн|Гн|мВт|Вт|%|°C|раз|раза|периода|периодов|итерации|значений';
function nbsp(text) {
  return text
    .replace(new RegExp(`(\\d) (?=(${UNITS})(?![А-Яа-яЁё]))`, 'g'), `$1${NBSP}`)
    .replace(/(^|[\s(])(п\.|т\.|рис\.|№) (?=[\dа-яё])/g, `$1$2${NBSP}`)
    .replace(/ — /g, `${NBSP}— `);
}
function runs(text, base = {}) {
  const out = [];
  const re = /(_\{[^}]*\}|\^\{[^}]*\}|<i>.*?<\/i>|<b>.*?<\/b>)/g;
  const t = nbsp(text);
  let last = 0;
  let m;
  while ((m = re.exec(t)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: t.slice(last, m.index), ...base }));
    const tok = m[0];
    if (tok.startsWith('<i>')) out.push(...runs(tok.slice(3, -4), { ...base, italics: true }));
    else if (tok.startsWith('<b>')) out.push(...runs(tok.slice(3, -4), { ...base, bold: true }));
    else {
      const inner = tok.slice(2, -1);
      out.push(new TextRun({ text: inner, ...base, ...(tok[0] === '_' ? { subScript: true } : { superScript: true }) }));
    }
    last = m.index + tok.length;
  }
  if (last < t.length) out.push(new TextRun({ text: t.slice(last), ...base }));
  return out;
}

// ---------- документная модель ----------
class Doc {
  constructor() {
    this.blocks = [];
    this.num = {};               // id -> номер
    this.headings = [];
  }
  h(lvl, id, text) { this.blocks.push({ t: 'h', lvl, id, text }); }
  p(text, o = {}) { this.blocks.push({ t: 'p', text, o }); }
  eq(id, text) { this.blocks.push({ t: 'eq', id, text }); }
  fig(id, file, wcm, caption) { this.blocks.push({ t: 'fig', id, file, wcm, caption }); }
  tab(id, caption, cols, rows, o = {}) { this.blocks.push({ t: 'tab', id, caption, cols, rows, o }); }
  lst(id, caption, lines, o = {}) { this.blocks.push({ t: 'lst', id, caption, lines, o }); }
  list(items, o = {}) { this.blocks.push({ t: 'list', items, o }); }
  raw(fn) { this.blocks.push({ t: 'raw', fn }); }

  numberAll() {
    const c = { fig: 0, tab: 0, lst: 0, eq: 0 };
    for (const b of this.blocks) {
      if (['fig', 'tab', 'lst', 'eq'].includes(b.t) && !(b.t === 'lst' && !b.caption)) {
        c[b.t] += 1;
        b.n = c[b.t];
        if (b.id) {
          if (this.num[b.t + ':' + b.id]) throw new Error('duplicate id ' + b.id);
          this.num[b.t + ':' + b.id] = b.n;
        }
      }
      if (b.t === 'h') this.headings.push({ id: b.id, lvl: b.lvl, text: b.text });
    }
  }

  ref(text) {
    return text.replace(/@(fig|tab|lst|eq):([\w-]+)/g, (all, k, id) => {
      const v = this.num[k + ':' + id];
      if (!v) throw new Error('unknown ref ' + all);
      return String(v);
    });
  }
}

// ---------- рендеринг ----------
const BODY = { spacing: { lineRule: 'auto', line: 360, before: 0, after: 0 } };

function para(doc, text, o = {}) {
  const t = doc.ref(text);
  return new Paragraph({
    children: runs(t, o.run || {}),
    alignment: o.center ? AlignmentType.CENTER : (o.left ? AlignmentType.LEFT : AlignmentType.JUSTIFIED),
    indent: o.noind || o.center ? undefined : { firstLine: 709 },
    spacing: { lineRule: 'auto', line: o.line || 360, before: o.before || 0, after: o.after || 0 },
    keepNext: !!o.keepNext,
    keepLines: true,
  });
}

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), buf: b };
}

function borders(color = '000000', size = 4) {
  const s = { style: BorderStyle.SINGLE, size, color };
  return { top: s, bottom: s, left: s, right: s };
}

function render(doc, figDir) {
  const out = [];
  for (const b of doc.blocks) {
    if (b.t === 'raw') { out.push(...b.fn()); continue; }
    if (b.t === 'h') {
      const lvlMap = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 };
      out.push(new Paragraph({
        heading: lvlMap[b.lvl],
        pageBreakBefore: b.lvl === 1,
        keepNext: true,
        keepLines: true,
        children: [new Bookmark({ id: b.id, children: runs(b.text) })],
      }));
      continue;
    }
    if (b.t === 'p') { out.push(para(doc, b.text, b.o)); continue; }
    if (b.t === 'eq') {
      const t = doc.ref(b.text);
      out.push(new Paragraph({
        tabStops: [{ type: TabStopType.CENTER, position: Math.round(TW / 2) }, { type: TabStopType.RIGHT, position: TW }],
        spacing: { lineRule: 'auto', line: 360, before: 60, after: 60 },
        keepLines: true,
        children: [new TextRun('\t'), ...runs(t), new TextRun(`\t(${b.n})`)],
      }));
      continue;
    }
    if (b.t === 'fig') {
      const { w, h, buf } = pngSize(path.join(figDir, b.file));
      const wpx = b.wcm / 2.54 * 96;
      const hpx = wpx * h / w;
      out.push(new Paragraph({
        alignment: AlignmentType.CENTER, keepNext: true, keepLines: true,
        spacing: { lineRule: 'auto', before: 120, after: 60, line: 240 },
        children: [new ImageRun({ type: 'png', data: buf, transformation: { width: Math.round(wpx), height: Math.round(hpx) } })],
      }));
      out.push(new Paragraph({
        alignment: AlignmentType.CENTER, keepLines: true,
        spacing: { lineRule: 'auto', before: 0, after: 200, line: 276 },
        children: runs(doc.ref(`Рисунок ${b.n} – ${b.caption}`)),
      }));
      continue;
    }
    if (b.t === 'tab') {
      out.push(new Paragraph({
        alignment: AlignmentType.LEFT, keepNext: true, keepLines: true,
        spacing: { lineRule: 'auto', before: 120, after: 60, line: 276 },
        children: runs(doc.ref(`Таблица ${b.n} – ${b.caption}`)),
      }));
      const widths = b.cols.map((c) => Math.round(c.w * CM));
      const scale = TW / widths.reduce((a, x) => a + x, 0);
      const W = widths.map((x) => Math.floor(x * Math.min(1, scale)));
      const total = W.reduce((a, x) => a + x, 0);
      const fs12 = b.o.size || 24;
      const keepAll = b.rows.length <= 15;
      const mkCell = (txt, i, hdr, extra = {}, keep = false) => new TableCell({
        width: { size: W[i], type: WidthType.DXA },
        verticalAlign: VerticalAlign.CENTER,
        margins: { top: 40, bottom: 40, left: 80, right: 80 },
        shading: hdr ? { type: ShadingType.CLEAR, color: 'auto', fill: 'E7E7E7' } : undefined,
        ...extra,
        children: String(txt).split('\n').map((line) => new Paragraph({
          alignment: (b.cols[i].align === 'left' && !hdr) ? AlignmentType.LEFT : AlignmentType.CENTER,
          spacing: { lineRule: 'auto', line: 240, before: 0, after: 0 },
          keepNext: keep,
          keepLines: true,
          children: runs(doc.ref(line), { size: fs12, bold: hdr || undefined }),
        })),
      });
      const rows = [new TableRow({ tableHeader: true, cantSplit: true, children: b.cols.map((c, i) => mkCell(c.h, i, true, {}, keepAll)) })];
      b.rows.forEach((r, ri) => {
        const keep = keepAll && ri < b.rows.length - 1;
        const cells = [];
        let ci = 0;
        for (const v of r) {
          if (v && typeof v === 'object' && v.span !== undefined) {
            cells.push(mkCell(v.text, ci, false, { rowSpan: v.span }, keep));
          } else if (v && typeof v === 'object' && v.skip) {
            // ячейка, занятая rowSpan сверху
          } else {
            cells.push(mkCell(v, ci, false, {}, keep));
          }
          ci += 1;
        }
        rows.push(new TableRow({ cantSplit: true, children: cells }));
      });
      out.push(new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: W, rows, alignment: AlignmentType.CENTER }));
      out.push(new Paragraph({ spacing: { lineRule: 'auto', line: 240, before: 0, after: 120 }, children: [] }));
      continue;
    }
    if (b.t === 'lst') {
      if (b.caption) {
        out.push(new Paragraph({
          alignment: AlignmentType.LEFT, keepNext: true, keepLines: true,
          spacing: { lineRule: 'auto', before: 120, after: 60, line: 276 },
          children: runs(doc.ref(`Листинг ${b.n} – ${b.caption}`)),
        }));
      }
      const size = b.o.size || 19;
      const lines = b.lines.map((line, i) => new Paragraph({
        spacing: { lineRule: 'auto', line: 240, before: 0, after: 0 },
        keepNext: i < b.lines.length - 1 && b.lines.length < 16,
        children: [new TextRun({ text: line.length ? line : ' ', font: MONO, size })],
      }));
      out.push(new Table({
        width: { size: TW, type: WidthType.DXA },
        columnWidths: [TW],
        rows: [new TableRow({ cantSplit: b.lines.length < 16, children: [new TableCell({
          width: { size: TW, type: WidthType.DXA },
          borders: borders('8C8C8C', 4),
          shading: { type: ShadingType.CLEAR, color: 'auto', fill: 'F4F4F4' },
          margins: { top: 60, bottom: 60, left: 100, right: 60 },
          children: lines,
        })] })],
      }));
      out.push(new Paragraph({ spacing: { lineRule: 'auto', line: 240, before: 0, after: 120 }, children: [] }));
      continue;
    }
    if (b.t === 'list') {
      const ref = b.o.numbered ? 'num' + (b.o.instance || 0) : 'dash';
      b.items.forEach((it, i) => out.push(new Paragraph({
        numbering: { reference: ref, level: 0 },
        alignment: b.o.left ? AlignmentType.LEFT : AlignmentType.JUSTIFIED,
        spacing: { lineRule: 'auto', line: 360, before: 0, after: 0 },
        keepLines: true,
        keepNext: !!b.o.keepNext,
        children: runs(doc.ref(it)),
      })));
      continue;
    }
    throw new Error('unknown block ' + b.t);
  }
  return out;
}

function numberingConfig(nNumbered) {
  const cfg = [{
    reference: 'dash',
    levels: [{ level: 0, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 1069, hanging: 360 } }, run: { font: FONT } } }],
  }];
  for (let i = 0; i < nNumbered; i++) {
    cfg.push({
      reference: 'num' + i,
      levels: [{ level: 0, format: LevelFormat.DECIMAL, text: i === 0 ? '%1.' : '%1)', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 1129, hanging: 420 } } } }],
    });
  }
  return cfg;
}

module.exports = { Doc, render, runs, n, sgn, dev, TW, CM, FONT, MONO, numberingConfig, borders };
