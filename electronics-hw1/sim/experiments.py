"""Все расчёты ДЗ-1 (вариант 30) в ngspice: netlist-ы, циклы подбора, финальные прогоны.

Netlist-ы (runs/*.cir) в том виде, в каком они приведены в отчёте; ngspice запускается
в каталоге runs/, результаты .meas берутся из лога, данные для графиков — из runs/*.raw.
Итог: results.json.
"""
import json
import os
import re
import subprocess

from spice import RUNS

T = 1 / 60
W0, W1 = 0.2, 0.2 + 4 * T          # окно измерений: 4 периода установившегося режима
WIN = f'from={W0} to={W1:.7f}'

MODEL_D = '.model D_Mosyagin D(IS=3p N=1.05 RS=10m TT=5n CJO=7p)'
# модели стабилитронов/диодов из библиотеки LTspice (standard.dio); параметры Tbv1, Nbvl, Ibvl,
# которые понимает только LTspice, убраны (ngspice их всё равно игнорирует с предупреждением)
ZLIB = {
    'BZX84C12VL': ('.model BZX84C12VL_Mosyagin D(Is=926.42E-18 N=1.062\n'
                   '+ Rs=231.3m Ikf=4.908 Cjo=18.08p M=305.6m Vj=568m\n'
                   '+ Isr=4.364p Nr=4 Bv=12 Ibv=5m tt=185n Nbv=300m)'),
    'BZX84C12L': '.model BZX84C12L_Mosyagin D(Is=.6n Rs=.5 Cjo=150p Nbv=5 Bv=12 Ibv=1m)',
    'BZX84C11VL': ('.model BZX84C11VL_Mosyagin D(Is=860.70E-18 N=1.063\n'
                   '+ Rs=281.7m Ikf=305.4m Cjo=20.32p M=311.6m Vj=564.5m\n'
                   '+ Isr=1.336p Nr=2.84 Bv=11 Ibv=5m tt=163n Nbv=250m)'),
    'BZX84C10L': '.model BZX84C10L_Mosyagin D(Is=.6n Rs=.5 Cjo=150p Nbv=5 Bv=10 Ibv=1m)',
    'BZX84C6V2L': '.model BZX84C6V2L_Mosyagin D(Is=1.5n Rs=.5 Cjo=185p Nbv=3 Bv=6.2 Ibv=1m)',
    '1N4148': '.model 1N4148_Mosyagin D(Is=2.52n Rs=.568 N=1.752 Cjo=4p M=.4 tt=20n)',
}
MODEL_Z = ZLIB['BZX84C12VL']
CHAIN0 = [('BZX84C12VL', 'Z')]
OPT = '.options reltol=1e-5 abstol=1e-12 vntol=1e-7 method=gear'
TRAN = 'tran 10u 0.27 0 10u uic'


def chain_lines(parts):
    """Ветвь стабилизатора от узла out к земле: стабилитроны — в обратном включении,
    диоды — в прямом. Возвращает строки элементов и нужные модели."""
    lines, models, node = [], [], 'out'
    nz = nd = 0
    for i, (name, kind) in enumerate(parts):
        nxt = '0' if i == len(parts) - 1 else f'z{i + 1}'
        if kind == 'Z':
            nz += 1
            lines.append(f'DZ{nz} {nxt} {node} {name}_Mosyagin')
        else:
            nd += 1
            lines.append(f'DS{nd} {node} {nxt} {name}_Mosyagin')
        if ZLIB[name] not in models:
            models.append(ZLIB[name])
        node = nxt
    return lines, models


def circuit(kind, stab, ktr, cf, vm=325.27, r1=None, parts=CHAIN0):
    """Схемная часть netlist (без управляющего блока)."""
    f = 'f' if stab else 'out'
    L = ['* IVEP Mosyagin, var. 30: ' + ('half-wave' if kind == 'hw' else 'bridge') + ' rectifier'
         + (' + stabilizer' if stab else ''),
         'V1 in 0 SIN(0 {Vm} 60)',
         'L1 in 0 {Ktr*Ktr*1u}']
    if kind == 'hw':
        L += ['L2 sec 0 1u', 'K1 L1 L2 0.99', 'VA1 sec a 0', f'D1 a {f} D_Mosyagin']
    else:
        L += ['L2 sec b 1u', 'K1 L1 L2 0.99', 'VA1 sec a 0',
              f'D1 a {f} D_Mosyagin', f'D2 b {f} D_Mosyagin',
              'D3 0 a D_Mosyagin', 'D4 0 b D_Mosyagin']
    L += [f'C1 {f} 0 {{Cf}}']
    if stab:
        zl, zm = chain_lines(parts)
        L += ['R1 f out {R1}'] + zl
    L += ['Rn out 0 3k', MODEL_D]
    if stab:
        L += zm
    p = f'.param Vm={vm} Ktr={ktr} Cf={cf}'
    if stab:
        p += f' R1={r1}'
    L += [p, OPT]
    return '\n'.join(L) + '\n'


def meas_block(stab, indent=''):
    m = [f'meas tran Uavg AVG v(out) {WIN}',
         f'meas tran Upp PP v(out) {WIN}',
         f'meas tran Umax MAX v(out) {WIN}',
         f'meas tran Umin MIN v(out) {WIN}',
         'let Kp = 100*Upp/Uavg']
    if stab:
        m += [f'meas tran Ufavg AVG v(f) {WIN}',
              f'meas tran Ufpp PP v(f) {WIN}',
              'let Kpf = 100*Ufpp/Ufavg',
              f'meas tran Izavg AVG @dz1[id] {WIN}',
              f'meas tran Izmin MIN @dz1[id] {WIN}',
              f'meas tran Izmax MAX @dz1[id] {WIN}']
    return '\n'.join(indent + x for x in m)


def cur_block(kind, stab):
    """Входной ток выпрямителя, время установления, обратное напряжение на диодах."""
    f = 'v(f)' if stab else 'v(out)'
    m = ['let ia = abs(i(VA1))',
         'meas tran Ipusk MAX ia from=0 to=0.0333333',
         f'meas tran Ipk MAX ia {WIN}',
         f'meas tran Irms RMS i(VA1) {WIN}',
         f'meas tran Iavg AVG i(VA1) {WIN}',
         f'meas tran Iabs AVG ia {WIN}',
         'let thr = 0.01*Ipk',
         'meas tran ton WHEN ia=$&thr RISE=1 TD=0.2',
         'meas tran toff WHEN ia=$&thr FALL=1 TD=$&ton',
         'let tw = toff - ton',
         'let thr2 = Umin - 0.001*Uavg',
         'meas tran tset WHEN v(out)=$&thr2 CROSS=LAST',
         f'let ud1 = {f} - v(a)',
         f'meas tran Urev1 MAX ud1 {WIN}']
    if kind == 'br':
        m += ['let ud3 = v(a)', f'meas tran Urev3 MAX ud3 {WIN}']
    return '\n'.join(m)


def ngspice(name, text):
    open(os.path.join(RUNS, name + '.cir'), 'w').write(text)
    subprocess.run(['ngspice', '-b', '-o', name + '.log', name + '.cir'], cwd=RUNS, capture_output=True)
    return open(os.path.join(RUNS, name + '.log'), encoding='latin-1').read()


VAL = r'([-+]?[0-9.]+(?:e[-+]?\d+)?)'


def parse_values(log):
    """Значения из строк meas («uavg = 1.2e+01 from= ...») и print («kp = 4.6e+01»)."""
    res = {}
    for m in re.finditer(r'^(\w+)\s+=\s+' + VAL, log, re.M | re.I):
        res[m.group(1).lower()] = float(m.group(2))
    return res


def sweep(name, kind, param, values, ktr, cf, stab=False, r1=None, vm=325.27, write_raw=False):
    """Цикл подбора: foreach + alterparam (аналог .step в LTspice)."""
    ctrl = ['.control', f'foreach val {" ".join(values)}',
            f'  alterparam {param} = $val', '  reset']
    if stab:
        ctrl.append('  save all @dz1[id]')
    ctrl += ['  ' + TRAN, meas_block(stab, '  ')]
    echo = f'  echo "{param} = $val:  Uavg = $&Uavg  Upp = $&Upp  Kp = $&Kp'
    echo += '  Ufavg = $&Ufavg  Izavg = $&Izavg"' if stab else '"'
    ctrl.append(echo)
    if write_raw:
        ctrl.append(f'  write {name}_$val v(sec) v(out)' + (' v(b)' if kind == 'br' else ''))
    ctrl += ['  destroy all', 'end', '.endc', '.end']
    text = circuit(kind, stab, ktr, cf, vm=vm, r1=r1) + '\n'.join(ctrl) + '\n'
    log = ngspice(name, text)
    rows = []
    for line in log.splitlines():
        if line.startswith(param + ' = '):
            val = line.split()[2].rstrip(':')
            nums = dict(re.findall(r'(\w+) = ' + VAL, line.split(':', 1)[1]))
            rows.append({'val': val, **{k: float(v) for k, v in nums.items()}})
    return text, log, rows


def single(name, kind, ktr, cf, stab=False, r1=None, vm=325.27, save='v(in) v(sec) v(out) i(VA1)',
           parts=CHAIN0, cur=False):
    """Одиночный прогон: измерения + запись данных для графиков."""
    if kind == 'br' and 'v(sec)' in save:
        save += ' v(b)'
    ctrl = ['.control']
    if stab:
        save += ' v(f) @dz1[id]'
        ctrl.append('save all @dz1[id]')
    ctrl += [TRAN, meas_block(stab)]
    if cur:
        ctrl.append(cur_block(kind, stab))
    ctrl += ['print Kp' + (' Kpf' if stab else '') + (' tw' if cur else ''),
             f'write {name}.raw {save}', '.endc', '.end']
    text = circuit(kind, stab, ktr, cf, vm=vm, r1=r1, parts=parts) + '\n'.join(ctrl) + '\n'
    log = ngspice(name, text)
    v = parse_values(log)
    keys = ['Uavg', 'Upp', 'Umax', 'Umin', 'Kp']
    if stab:
        keys += ['Ufavg', 'Ufpp', 'Kpf', 'Izavg', 'Izmin', 'Izmax']
    if cur:
        keys += ['Ipusk', 'Ipk', 'Irms', 'Iavg', 'Iabs', 'ton', 'toff', 'tw', 'tset', 'Urev1']
        if kind == 'br':
            keys.append('Urev3')
    return text, log, {k: v[k.lower()] for k in keys}


def main():
    R = {}
    # ---------------- Задание 1: однополупериодный ----------------
    R['hw_a'] = single('hw_a', 'hw', 10, '10u')[2]
    R['hw_b_sweep'] = sweep('hw_b_sweep', 'hw', 'Ktr', ['18', '19', '20', '21', '22'], 10, '10u',
                            write_raw=True)[2]
    R['hw_b'] = single('hw_b', 'hw', 20, '10u')[2]
    R['hw_v_it1'] = sweep('hw_v_it1', 'hw', 'Cf', [f'{c}u' for c in range(100, 1001, 100)], 20, '10u')[2]
    R['hw_v_it2'] = sweep('hw_v_it2', 'hw', 'Cf', [f'{c}u' for c in range(600, 701, 10)], 20, '10u')[2]
    R['hw_v'] = single('hw_v', 'hw', 20, '680u')[2]
    for tag, c in [('c10', '68u'), ('c1', '680u'), ('c100', '6.8m')]:
        R['hw_g_' + tag] = single('hw_g_' + tag, 'hw', 20, c, cur=True)[2]
    R['hw_d'] = single('hw_d', 'hw', 20, '680u', stab=True, r1=360, cur=True)[2]
    R['hw_e'] = single('hw_e', 'hw', 20, '680u', stab=True, r1=360, vm=357.80, cur=True)[2]
    R['hw_e_nostab'] = single('hw_e_nostab', 'hw', 20, '680u', vm=357.80, cur=True)[2]
    # ---------------- Задание 2: мостовой ----------------
    R['br_a'] = single('br_a', 'br', 10, '10u')[2]
    R['br_b_sweep'] = sweep('br_b_sweep', 'br', 'Ktr', ['20', '21', '22', '23', '24'], 10, '10u',
                            write_raw=True)[2]
    R['br_b'] = single('br_b', 'br', 22, '10u')[2]
    R['br_v_it1'] = sweep('br_v_it1', 'br', 'Cf', [f'{c}u' for c in range(100, 1001, 100)], 22, '10u')[2]
    R['br_v_it2'] = sweep('br_v_it2', 'br', 'Cf', [f'{c}u' for c in range(300, 401, 10)], 22, '10u')[2]
    R['br_v'] = single('br_v', 'br', 22, '320u')[2]
    for tag, c in [('c10', '32u'), ('c1', '320u'), ('c100', '3.2m')]:
        R['br_g_' + tag] = single('br_g_' + tag, 'br', 22, c, cur=True)[2]
    R['br_d'] = single('br_d', 'br', 22, '320u', stab=True, r1=130, cur=True)[2]
    R['br_e'] = single('br_e', 'br', 22, '320u', stab=True, r1=130, vm=357.80, cur=True)[2]
    R['br_e_nostab'] = single('br_e_nostab', 'br', 22, '320u', vm=357.80, cur=True)[2]
    json.dump(R, open(os.path.join(os.path.dirname(RUNS), 'results.json'), 'w'), indent=1)
    for k, v in R.items():
        print(k, v if not isinstance(v, list) else '\n  ' + '\n  '.join(str(r) for r in v))


if __name__ == '__main__':
    main()
