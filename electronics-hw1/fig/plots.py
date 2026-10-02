"""Графики для отчёта по ДЗ-1 (данные — raw-файлы ngspice из sim/runs).

Оформление по методичке: тёмные линии на белом фоне, соотношение сторон поля графика
от 1:3 до 3:1, по оси X для периодических сигналов — ровно 4 периода, ось Y — без пустых полей.
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, FuncFormatter, MultipleLocator, FixedLocator, NullFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, '..', 'sim')
sys.path.insert(0, SIM)
from spice import read_raw  # noqa: E402

RUNS = os.path.join(SIM, 'runs')
RES = json.load(open(os.path.join(SIM, 'results.json')))
EXTRA = json.load(open(os.path.join(SIM, 'extra.json')))

T = 1000 / 60                  # период, мс
SS = (200.0, 200.0 + 4 * T)    # окно установившегося режима (4 периода), мс
ST = (0.0, 4 * T)              # первые 4 периода (включение), мс
W = 6.3                        # ширина рисунка, дюймы (16 см)

plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Liberation Serif', 'DejaVu Serif'],
    'mathtext.fontset': 'custom', 'mathtext.rm': 'Liberation Serif',
    'mathtext.it': 'Liberation Serif:italic', 'mathtext.bf': 'Liberation Serif:bold',
    'font.size': 11, 'axes.titlesize': 11, 'axes.labelsize': 11, 'legend.fontsize': 10.5,
    'xtick.labelsize': 10.5, 'ytick.labelsize': 10.5,
    'axes.linewidth': 0.9, 'axes.edgecolor': 'black', 'axes.facecolor': 'white',
    'figure.facecolor': 'white', 'savefig.facecolor': 'white',
    'axes.grid': True, 'grid.color': '#9a9a9a', 'grid.linestyle': ':', 'grid.linewidth': 0.7,
    'xtick.direction': 'in', 'ytick.direction': 'in', 'xtick.top': True, 'ytick.right': True,
    'legend.frameon': False, 'legend.handlelength': 2.6, 'legend.columnspacing': 1.4,
    'lines.linewidth': 1.5, 'axes.unicode_minus': True,
})

BLACK, BLUE, RED, GREEN, GRAY = '#000000', '#16307a', '#8a0f0f', '#1d4f22', '#4a4a4a'
S_MAIN = dict(color=BLACK, lw=1.6, ls='-')
S_2 = dict(color=BLUE, lw=1.4, ls='--')
S_3 = dict(color=RED, lw=1.4, ls='-.')
S_4 = dict(color=GREEN, lw=1.4, ls=':')


def num(x, nd):
    return f'{x:.{nd}f}'.replace('.', ',').replace('-', '−')


class Comma(ScalarFormatter):
    def __init__(self):
        super().__init__(useOffset=False, useMathText=False)
        self.set_powerlimits((-6, 7))

    def __call__(self, x, pos=None):
        return super().__call__(x, pos).replace('.', ',')


def comma_axes(ax, x=True, y=True):
    if x:
        ax.xaxis.set_major_formatter(Comma())
    if y:
        ax.yaxis.set_major_formatter(Comma())


def time_axis(ax, window, label=True):
    t0 = window[0]
    ticks = [t0 + k * T for k in range(5)]
    ax.set_xlim(window)
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: num(v, 1)))
    ax.xaxis.set_minor_locator(FixedLocator([t0 + k * T / 4 for k in range(17)]))
    ax.grid(True, which='major')
    if label:
        ax.set_xlabel('t, мс')


def tight_y(ax, arrays, pad=0.06, lo=None, hi=None):
    mn = min(float(np.min(a)) for a in arrays)
    mx = max(float(np.max(a)) for a in arrays)
    r = (mx - mn) or (abs(mx) * 0.01 or 1.0)
    ax.set_ylim(mn - pad * r if lo is None else lo, mx + pad * r if hi is None else hi)


def head(ax, legend=True, meas=None, ncol=4):
    """Легенда над полем графика слева, результаты измерений — справа."""
    if legend:
        ax.legend(loc='lower left', bbox_to_anchor=(0.0, 1.0), ncol=ncol, borderaxespad=0.15,
                  handletextpad=0.5)
    if meas:
        ax.set_title(meas, loc='right', pad=5, fontsize=10.5)


def check_aspect(fig, name):
    fig.canvas.draw()
    for ax in fig.axes:
        bb = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        r = bb.width / bb.height
        assert 1 / 3 <= r <= 3, f'{name}: aspect {r:.2f}'


def save(fig, name):
    check_aspect(fig, name)
    fig.savefig(os.path.join(HERE, name + '.png'), dpi=220)
    plt.close(fig)
    print('saved', name)


def raw(name):
    path = os.path.join(RUNS, name + '.raw')
    d = read_raw(path if os.path.exists(path) else os.path.join(RUNS, name))
    d['t'] = d['time'] * 1e3
    return d


def win(d, window):
    m = (d['t'] >= window[0] - 1e-9) & (d['t'] <= window[1] + 1e-9)
    return {k: v[m] for k, v in d.items()}


def kfmt(k):
    return num(k, 4 if k < 0.1 else 3 if k < 10 else 2)


def ufmt(u):
    return num(u, 5 if u < 0.01 else 4 if u < 1 else 3)


def meas_text(r, node='out', nd=3):
    """Подпись с результатами .meas (значения из лога ngspice)."""
    if node == 'f':
        return (f'V(f): $U_\\mathrm{{ср}}$ = {num(r["Ufavg"], nd)} В,  $U_\\mathrm{{pp}}$ = {ufmt(r["Ufpp"])} В,'
                f'  $K_\\mathrm{{п}}$ = {kfmt(r["Kpf"])} %')
    return (f'V({node}): $U_\\mathrm{{ср}}$ = {num(r["Uavg"], nd)} В,  $U_\\mathrm{{pp}}$ = {ufmt(r["Upp"])} В,'
            f'  $K_\\mathrm{{п}}$ = {kfmt(r["Kp"])} %')


def vin_label(kind):
    return ('V(sec)', 'sec') if kind == 'hw' else ('V(sec,b)', 'sec,b')


def vsec(d, kind):
    return d['v(sec)'] if kind == 'hw' else d['v(sec)'] - d['v(b)']


# ---------------------------------------------------------------------------
def fig_sec_out(kind, run, name):
    """Пункты а, б: напряжение на входе выпрямителя и на выходе, 4 периода."""
    d = win(raw(run), SS)
    r = RES[run]
    fig, ax = plt.subplots(figsize=(W, 3.15), layout='constrained')
    lab, _ = vin_label(kind)
    ax.plot(d['t'], vsec(d, kind), label=lab, **S_2)
    ax.plot(d['t'], d['v(out)'], label='V(out)', **S_MAIN)
    time_axis(ax, SS)
    tight_y(ax, [vsec(d, kind), d['v(out)']], pad=0.04)
    comma_axes(ax, x=False)
    ax.set_ylabel('U, В')
    head(ax, meas=meas_text(r))
    save(fig, name)


def fig_ktr_sweep(kind, name, vals, chosen):
    """Пункт б: семейство V(out) при переборе Kтр (аналог .step в LTspice)."""
    fig, ax = plt.subplots(figsize=(W, 3.3), layout='constrained')
    styles = [dict(color=GRAY, lw=1.1, ls='--'), dict(color=BLUE, lw=1.1, ls='-.'), dict(color=RED, lw=1.1, ls=':'),
              dict(color=GREEN, lw=1.1, ls=(0, (5, 2, 1, 2))), dict(color=BLUE, lw=1.1, ls=(0, (1, 1)))]
    arrs = []
    k = 0
    for v in vals:
        d = win(raw(f'{kind}_b_sweep_{v}'), SS)
        arrs.append(d['v(out)'])
        if v == chosen:
            ax.plot(d['t'], d['v(out)'], label=f'$K_\\mathrm{{тр}}$ = {v}', **S_MAIN)
        else:
            ax.plot(d['t'], d['v(out)'], label=f'$K_\\mathrm{{тр}}$ = {v}', **styles[k])
            k += 1
    ax.axhline(12, color=BLACK, lw=0.9, ls=(0, (8, 3)))
    ax.text(SS[0] + 4.6, 11.93, '12 В', va='top', fontsize=10.5, bbox=dict(fc='white', ec='none', pad=0.6))
    time_axis(ax, SS)
    tight_y(ax, arrs, pad=0.04)
    comma_axes(ax, x=False)
    ax.set_ylabel('V(out), В')
    head(ax, ncol=5)
    save(fig, name)


def fig_kc(kind, name, chosen_uf):
    """Пункт в: итерации подбора ёмкости фильтра."""
    it = [EXTRA[f'{kind}_v_it0'], RES[f'{kind}_v_it1'], RES[f'{kind}_v_it2']]
    cap = lambda rows: np.array([float(r['val'].rstrip('u')) for r in rows])
    kp = lambda rows: np.array([r['Kp'] if 'Kp' in r else r['kp'] for r in rows])
    fig, ax = plt.subplots(figsize=(W, 3.9), layout='constrained')
    lo2, hi2 = int(cap(it[2])[0]), int(cap(it[2])[-1])
    ax.plot(cap(it[0]), kp(it[0]), ls='none', marker='.', ms=5, color=GRAY,
            label='итерация 0: 1…50 мкФ, шаг 1 мкФ')
    ax.plot(cap(it[1]), kp(it[1]), ls='none', marker='o', ms=6, mfc='white', mec=BLACK, mew=1.2,
            label='итерация 1: 100…1000 мкФ, шаг 100 мкФ')
    ax.plot(cap(it[2]), kp(it[2]), ls='none', marker='s', ms=4.5, color=BLUE,
            label=f'итерация 2: {lo2}…{hi2} мкФ, шаг 10 мкФ')
    c = np.logspace(0, 3.05, 200)
    est = 100 / (3000 * c * 1e-6 * 60) * (1 if kind == 'hw' else 0.5)
    ax.plot(c, est, color=BLACK, lw=1.0, ls=':', label='оценка по формуле ' + ('(13)' if kind == 'hw' else '(14)'))
    ax.axhline(0.78, color=RED, lw=1.1, ls='--', label='$K_\\mathrm{п}$ = 0,78 %')
    ax.axvline(chosen_uf, color=BLACK, lw=0.9, ls='-.')
    ax.text(chosen_uf * 1.04, 30, f'$C_{{ф1}}$ = {chosen_uf} мкФ', fontsize=10.5, rotation=90, va='center')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(0.9, 1150)
    ax.set_ylim(0.3 if kind == 'hw' else 0.15, 300 if kind == 'hw' else 150)
    f = FuncFormatter(lambda v, p: ('%g' % v).replace('.', ','))
    ax.xaxis.set_major_formatter(f)
    ax.yaxis.set_major_formatter(f)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.grid(True, which='minor', color='#c8c8c8', ls=':', lw=0.5)
    ax.set_xlabel('$C_1$, мкФ')
    ax.set_ylabel('$K_\\mathrm{п}$, %')
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2, fontsize=10, borderaxespad=0.15,
              columnspacing=1.0)
    save(fig, name)


def fig_out(kind, run, name, node='out'):
    """Пункт в: выходное напряжение при Cф1, 4 периода."""
    d = win(raw(run), SS)
    fig, ax = plt.subplots(figsize=(W, 3.0), layout='constrained')
    ax.plot(d['t'], d[f'v({node})'], label=f'V({node})', **S_MAIN)
    time_axis(ax, SS)
    tight_y(ax, [d[f'v({node})']], pad=0.08)
    comma_axes(ax, x=False)
    ax.set_ylabel('V(out), В')
    head(ax, meas=meas_text(RES[run], node))
    save(fig, name)


def fig_g_start(kind, name, caps):
    """Пункт г: V(out) и I(VA1) для Cф1/10, Cф1, 10·Cф1 — включение и выход в установившийся режим."""
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(W, 5.3), layout='constrained', sharex=True)
    styles = {'c10': S_3, 'c1': S_MAIN, 'c100': S_2}
    order = ['c100', 'c1', 'c10']
    vs, cs = [], []
    for tag in order:
        d = win(raw(f'{kind}_g_{tag}'), ST)
        lab = caps[tag]
        a1.plot(d['t'], d['v(out)'], label=lab, **styles[tag])
        a2.plot(d['t'], d['i(va1)'], label=lab, **styles[tag])
        vs.append(d['v(out)'])
        cs.append(d['i(va1)'])
    for a in (a1, a2):
        time_axis(a, ST, label=(a is a2))
        comma_axes(a, x=False)
    tight_y(a1, vs, pad=0.04)
    tight_y(a2, cs, pad=0.04)
    a1.set_ylabel('V(out), В')
    a2.set_ylabel('I(VA1), А')
    h, l = a1.get_legend_handles_labels()
    a1.legend(h[::-1], l[::-1], loc='lower left', bbox_to_anchor=(0, 1.0), ncol=3, borderaxespad=0.15)
    a2.set_title('входной ток выпрямителя (ток вторичной обмотки)', loc='right', pad=5, fontsize=10.5)
    # подписи пиков пускового тока
    for tag in order:
        d = win(raw(f'{kind}_g_{tag}'), ST)
        k = int(np.argmax(np.abs(d['i(va1)'])))
        pk = d['i(va1)'][k]
        a2.annotate(f'{num(pk, 2 if abs(pk) < 10 else 1)} А', xy=(d['t'][k], pk),
                    xytext=(d['t'][k] + 3.0 + (4 if tag == 'c10' else 0), pk - 0.07 * (a2.get_ylim()[1] - a2.get_ylim()[0]) if tag == 'c100' else pk + 0.08 * (a2.get_ylim()[1] - a2.get_ylim()[0])),
                    fontsize=10, arrowprops=dict(arrowstyle='-', color=GRAY, lw=0.8))
    save(fig, name)


def fig_g_steady(kind, name, caps):
    """Пункт г: те же величины в установившемся режиме (4 периода)."""
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(W, 5.3), layout='constrained', sharex=True)
    styles = {'c10': S_3, 'c1': S_MAIN, 'c100': S_2}
    order = ['c10', 'c1', 'c100']
    vs, cs = [], []
    for tag in order:
        d = win(raw(f'{kind}_g_{tag}'), SS)
        a1.plot(d['t'], d['v(out)'], label=caps[tag], **styles[tag])
        a2.plot(d['t'], d['i(va1)'] * 1e3, label=caps[tag], **styles[tag])
        vs.append(d['v(out)'])
        cs.append(d['i(va1)'] * 1e3)
    for a in (a1, a2):
        time_axis(a, SS, label=(a is a2))
        comma_axes(a, x=False)
    tight_y(a1, vs, pad=0.05)
    tight_y(a2, cs, pad=0.04)
    a1.set_ylabel('V(out), В')
    a2.set_ylabel('I(VA1), мА')
    a1.legend(loc='lower left', bbox_to_anchor=(0, 1.0), ncol=3, borderaxespad=0.15)
    save(fig, name)


def fig_stab(kind, run, name):
    """Пункт д: напряжение на входе стабилизатора и на выходе."""
    d = win(raw(run), SS)
    r = RES[run]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(W, 5.3), layout='constrained', sharex=True)
    a1.plot(d['t'], d['v(f)'], label='V(f)', **S_2)
    a2.plot(d['t'], d['v(out)'], label='V(out)', **S_MAIN)
    tight_y(a1, [d['v(f)']], pad=0.08)
    tight_y(a2, [d['v(out)']], pad=0.08)
    for a in (a1, a2):
        time_axis(a, SS, label=(a is a2))
        comma_axes(a, x=False)
    a1.set_ylabel('V(f), В')
    a2.set_ylabel('V(out), В')
    head(a1, meas=meas_text(r, 'f'), ncol=1)
    head(a2, meas=meas_text(r, 'out', nd=4), ncol=1)
    save(fig, name)


def fig_plus10(kind, name):
    """Пункт е): входное и выходное напряжение при повышенном на 10 % напряжении сети (отдельные поля)."""
    dn = win(raw(f'{kind}_d'), SS)
    de = win(raw(f'{kind}_e'), SS)
    rn, re_ = RES[f'{kind}_d'], RES[f'{kind}_e']
    fig, (a1, a3) = plt.subplots(2, 1, figsize=(W, 5.3), layout='constrained', sharex=True)
    a1.plot(de['t'], de['v(in)'], label='V(in), +10 %', **S_MAIN)
    a1.plot(dn['t'], dn['v(in)'], label='V(in), номинал', **S_2)
    a3.plot(de['t'], de['v(out)'], label='V(out), +10 %', **S_MAIN)
    a3.plot(dn['t'], dn['v(out)'], label='V(out), номинал', **S_2)
    tight_y(a1, [de['v(in)']], pad=0.04)
    tight_y(a3, [de['v(out)'], dn['v(out)']], pad=0.08)
    for a in (a1, a3):
        time_axis(a, SS, label=(a is a3))
        comma_axes(a, x=False)
    a1.set_ylabel('V(in), В')
    a3.set_ylabel('V(out), В')
    head(a1, ncol=2, meas='амплитуда 357,80 В (253 В действ.)')
    head(a3, ncol=2)
    box = dict(boxstyle='square,pad=0.25', fc='white', ec='none')
    a3.text(0.985, 0.5, (f'+10 %:   $U_\\mathrm{{ср}}$ = {num(re_["Uavg"], 4)} В,  $K_\\mathrm{{п}}$ = {kfmt(re_["Kp"])} %\n'
                         f'номинал: $U_\\mathrm{{ср}}$ = {num(rn["Uavg"], 4)} В,  $K_\\mathrm{{п}}$ = {kfmt(rn["Kp"])} %'),
            transform=a3.transAxes, ha='right', va='center', fontsize=10.5, bbox=box)
    save(fig, name)


def fig_iv(name):
    """ВАХ моделей: прямая ветвь D_Mosyagin и участок пробоя BZX84C12VL_Mosyagin."""
    dd = read_raw(os.path.join(RUNS, 'iv_d.raw'))
    dz = read_raw(os.path.join(RUNS, 'iv_z.raw'))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 3.0), layout='constrained')
    v, i = dd['v(a)'], dd['i(id)']
    m = (v >= 0.45)
    a1.plot(v[m], i[m], label='D_Mosyagin', **S_MAIN)
    a1.set_xlim(0.45, 0.8)
    a1.set_ylim(-0.02, 1.0)
    for ipk, lab in [(RES and 0.287, 'однополуп.'), (0.089, 'мост')]:
        vv = np.interp(ipk, i, v)
        a1.plot([vv], [ipk], marker='o', ms=5, mfc='white', mec=BLACK)
        a1.annotate(f'{lab}: {num(ipk * 1e3, 0)} мА, {num(vv, 3)} В', xy=(vv, ipk), xytext=(0.455, ipk + 0.12),
                    fontsize=9.5, arrowprops=dict(arrowstyle='-', color=GRAY, lw=0.8))
    a1.set_xlabel('U, В')
    a1.set_ylabel('I, А')
    a1.legend(loc='upper left')
    vz, iz = dz['v(k)'], dz['i(iz)'] * 1e3
    a2.plot(vz, iz, label='BZX84C12VL_Mosyagin', **S_MAIN)
    a2.set_xlim(11.95, 12.02)
    a2.set_ylim(-0.5, 20)
    pts = [(-RES['hw_d']['Izavg'] * 1e3, None), (-RES['br_d']['Izavg'] * 1e3, 'номинал: 5,27 и 5,55 мА'),
           (-RES['hw_e']['Izavg'] * 1e3, f'+10 %: {num(-RES["hw_e"]["Izavg"] * 1e3, 2)} мА'),
           (-RES['br_e']['Izavg'] * 1e3, f'+10 %: {num(-RES["br_e"]["Izavg"] * 1e3, 2)} мА')]
    for izp, lab in pts:
        vv = np.interp(izp, iz, vz)
        a2.plot([vv], [izp], marker='o', ms=5, mfc='white', mec=BLACK)
        if lab:
            a2.annotate(lab, xy=(vv, izp), xytext=(vv - 0.0035, izp + 0.6), ha='right', fontsize=9.5,
                        arrowprops=dict(arrowstyle='-', color=GRAY, lw=0.8))
    a2.set_xlabel('$U_\\mathrm{обр}$, В')
    a2.set_ylabel('$I_\\mathrm{обр}$, мА')
    a2.legend(loc='upper left')
    for a in (a1, a2):
        comma_axes(a)
    a2.xaxis.set_major_locator(MultipleLocator(0.02))
    save(fig, name)


def main():
    caps_hw = {'c10': '$C_{ф1}$/10 = 68 мкФ', 'c1': '$C_{ф1}$ = 680 мкФ', 'c100': '10·$C_{ф1}$ = 6,8 мФ'}
    caps_br = {'c10': '$C_{ф1}$/10 = 32 мкФ', 'c1': '$C_{ф1}$ = 320 мкФ', 'c100': '10·$C_{ф1}$ = 3,2 мФ'}
    for kind, caps, cf1, vals, chosen in [('hw', caps_hw, 680, ['18', '19', '20', '21', '22'], '20'),
                                          ('br', caps_br, 320, ['20', '21', '22', '23', '24'], '22')]:
        fig_sec_out(kind, f'{kind}_a', f'{kind}_a')
        fig_ktr_sweep(kind, f'{kind}_b_sweep', vals, chosen)
        fig_sec_out(kind, f'{kind}_b', f'{kind}_b')
        fig_kc(kind, f'{kind}_kc', cf1)
        fig_out(kind, f'{kind}_v', f'{kind}_v')
        fig_g_start(kind, f'{kind}_g_start', caps)
        fig_g_steady(kind, f'{kind}_g_steady', caps)
        fig_stab(kind, f'{kind}_d', f'{kind}_d')
        fig_plus10(kind, f'{kind}_e')
    fig_iv('iv')


if __name__ == '__main__':
    main()
