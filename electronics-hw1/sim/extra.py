"""Дополнительные прогоны для отчёта: итерация 0 подбора Cф (1…50 мкФ), выбор состава
стабилизатора и R1, проверка при пониженном на 10 % напряжении сети, ВАХ моделей диодов."""
import json
import os
import re

from experiments import circuit, single, sweep, ngspice, MODEL_D, MODEL_Z
from spice import RUNS

VM = 325.27
FINAL = {'hw': dict(ktr=20, cf='680u', r1=360), 'br': dict(ktr=22, cf='320u', r1=130)}


def iv_curves():
    """DC-характеристики: прямая ветвь D_Mosyagin и пробой BZX84C12VL_Mosyagin."""
    text = '\n'.join([
        '* VAX diodov (Mosyagin)',
        'VD a 0 0',
        'D1 a 0 D_Mosyagin',
        'VZ k 0 0',
        'DZ1 0 k BZX84C12VL_Mosyagin',
        MODEL_D, MODEL_Z,
        '.control',
        'dc VD 0 0.8 0.5m',
        'let id = -i(VD)',
        'write iv_d.raw v(a) id',
        'dc VZ 10 12.2 0.2m',
        'let iz = -i(VZ)',
        'write iv_z.raw v(k) iz',
        '.endc', '.end']) + '\n'
    ngspice('iv', text)


def main():
    R = {}
    for kind in ('hw', 'br'):
        p = FINAL[kind]
        # итерация 0 по методичке: 1…50 мкФ с шагом 1 мкФ
        _, _, R[f'{kind}_v_it0'] = sweep(f'{kind}_v_it0', kind, 'Cf',
                                         [f'{c}u' for c in range(1, 51)], p['ktr'], '10u')
        # варианты состава стабилизатора при одном и том же R1
        opts = {
            'A': [('BZX84C12L', 'Z')],
            'B': [('BZX84C12VL', 'Z')],
            'C': [('BZX84C11VL', 'Z'), ('1N4148', 'D')],
            'D': [('BZX84C10L', 'Z'), ('1N4148', 'D'), ('1N4148', 'D')],
            'E': [('BZX84C6V2L', 'Z'), ('BZX84C6V2L', 'Z')],
        }
        for key, parts in opts.items():
            res = single(f'{kind}_stab_{key}', kind, p['ktr'], p['cf'], stab=True, r1=p['r1'],
                         parts=parts, save='v(out) v(f)')[2]
            res['Iz'] = -res['Izavg'] * 1e3
            R[f'{kind}_stab_{key}'] = res
        # подбор R1 для выбранного стабилитрона
        r1s = ['300', '330', '360', '390', '430'] if kind == 'hw' else ['110', '120', '130', '150', '160']
        _, _, rows = sweep(f'{kind}_r1', kind, 'R1', r1s, p['ktr'], p['cf'], stab=True, r1=p['r1'])
        for r in rows:
            r['Iz'] = -r['Izavg'] * 1e3
        R[f'{kind}_r1'] = rows
        # пониженное на 10 % напряжение сети (проверка запаса стабилизатора)
        res = single(f'{kind}_low', kind, p['ktr'], p['cf'], stab=True, r1=p['r1'], vm=round(VM * 0.9, 2))[2]
        res['Iz'] = -res['Izavg'] * 1e3
        R[f'{kind}_low'] = res
    iv_curves()
    json.dump(R, open(os.path.join(os.path.dirname(RUNS), 'extra.json'), 'w'), indent=1)
    for k, v in R.items():
        if isinstance(v, list):
            print(k)
            for r in v:
                print('   ', r)
        else:
            print(k, v)


if __name__ == '__main__':
    main()
