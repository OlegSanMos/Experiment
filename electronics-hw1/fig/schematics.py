"""Схемы ИВЭП для отчёта (по netlist-ам из sim/experiments.py).

Имена элементов и узлов совпадают с netlist: V1, L1, L2, K1, VA1, D1…D4, C1, R1, DZ1, Rn;
узлы in, sec, a, b, f, out.
"""
import math
import sys
import schemdraw
import schemdraw.elements as elm

FS = 19           # основной размер шрифта на схеме
schemdraw.config(font='Liberation Sans', fontsize=FS, lw=1.5, unit=2.0)


def node(xy, name, loc='top', ofst=0.12):
    """Метка узла (аналог Label Net в LTspice): точка + подпись."""
    elm.Dot(radius=0.075).at(xy)
    elm.Label().at(xy).label(name, loc=loc, ofst=ofst, fontsize=FS + 1)


def text(xy, lines, halign='center', valign='center', fs=FS):
    elm.Label().at(xy).label(lines if isinstance(lines, str) else '\n'.join(lines),
                             halign=halign, valign=valign, fontsize=fs)


def source_transformer(y_top):
    """V1, обмотки L1/L2 и K1. Возвращает (s1, s2) — выводы вторичной обмотки."""
    V1 = elm.SourceSin().at((0, 0)).up().length(y_top)
    text((-0.7, y_top / 2), ['V1', 'SIN(0 {Vm} 60)'], halign='right')
    elm.Ground().at(V1.start)
    elm.Line().at(V1.end).right().length(4.2)
    node((1.3, y_top), 'in')
    T = elm.Transformer(t1=6, t2=6).anchor('p1').at((4.2, y_top)).scale(1.2)
    ym = (T.p1[1] + T.p2[1]) / 2
    text((T.p1[0] - 0.4, ym - 0.1), ['L1', '{Ktr*Ktr*1u}'], halign='right')
    text((T.s1[0] + 0.4, ym - 0.1), ['L2', '1u'], halign='left')
    # точки начала обмоток (первые узлы L1 и L2 в netlist)
    elm.Dot(radius=0.09).at((T.p1[0] - 0.3, T.p1[1] - 0.35))
    elm.Dot(radius=0.09).at((T.s1[0] + 0.3, T.s1[1] - 0.35))
    text(((T.p1[0] + T.s1[0]) / 2 - 0.8, T.p1[1] + 0.95), 'K1 L1 L2 0.99')
    elm.Line().at(T.p2).down().toy(0)
    elm.Ground()
    return T.s1, T.s2


def stabilizer_and_load(x0, y, h):
    """R1, DZ1, Rn справа от узла f (x0 — точка подключения C1). h — высота вертикальных ветвей."""
    elm.Line().at((x0, y)).right().length(0.4)
    R = elm.Resistor().right().length(2.2)
    text((R.center[0], y + 0.55), 'R1')
    text((R.center[0], y - 0.6), '{R1}')
    L = elm.Line().right().length(1.0)
    node(L.center, 'out')
    x_z = L.end[0]
    elm.Zener().at((x_z, y)).down().length(h).reverse()
    text((x_z + 0.45, y - h / 2), ['DZ1', 'BZX84C12VL', '_Mosyagin'], halign='left')
    elm.Ground()
    elm.Line().at((x_z, y)).right().length(4.7)
    elm.Resistor().down().length(h)
    text((x_z + 4.7 + 0.45, y - h / 2), ['Rn', '3k'], halign='left')
    elm.Ground()


def load_only(x0, y, h):
    elm.Line().at((x0, y)).right().length(1.8)
    elm.Resistor().down().length(h)
    text((x0 + 1.8 + 0.45, y - h / 2), ['Rn', '3k'], halign='left')
    elm.Ground()


def capacitor(x, y, h):
    elm.Capacitor().at((x, y)).down().length(h)
    text((x + 0.45, y - h / 2), ['C1', '{Cf}'], halign='left')
    elm.Ground()


def halfwave(stab):
    with schemdraw.Drawing(show=False) as d:
        y = 3.0
        s1, s2 = source_transformer(y)
        elm.Line().at(s2).down().toy(0)
        elm.Ground()
        L = elm.Line().at(s1).right().length(1.8)
        node((L.end[0] - 0.95, y), 'sec')
        elm.MeterA().at(L.end).right().length(1.6).label('VA1', loc='top', ofst=0.1)
        L = elm.Line().right().length(0.9)
        node(L.center, 'a')
        elm.Diode().at(L.end).right().length(2.2).label('D1', loc='top').label('D_Mosyagin', loc='bottom', ofst=0.1)
        L = elm.Line().right().length(1.0)
        node(L.center, 'f' if stab else 'out')
        x_c = L.end[0]
        capacitor(x_c, y, y)
        if stab:
            stabilizer_and_load(x_c, y, y)
        else:
            load_only(x_c, y, y)
        return d


def bridge(stab):
    with schemdraw.Drawing(show=False) as d:
        y = 3.0
        s1, s2 = source_transformer(y)
        L = elm.Line().at(s1).right().length(1.8)
        node((L.end[0] - 0.95, y), 'sec')
        A = elm.MeterA().at(L.end).right().length(1.6).label('VA1', loc='top', ofst=0.1)
        elm.Line().right().length(0.3)
        # ромб моста: a — левая вершина, b — правая, f — верхняя, нижняя — земля
        side = 2.4
        h = side / math.sqrt(2)
        xa, ya = A.end[0] + 1.2, y - h
        elm.Line().down().toy(ya)
        elm.Line().right().tox(xa)
        node((xa - 0.45, ya), 'a', loc='top', ofst=0.12)
        top = (xa + h, ya + h)
        bot = (xa + h, ya - h)
        xb = xa + 2 * h
        elm.Diode().at((xa, ya)).theta(45).length(side).label('D1', loc='top', ofst=0.05)
        elm.Diode().at((xb, ya)).theta(135).length(side).label('D2', loc='top', ofst=0.05)
        elm.Diode().at(bot).theta(135).length(side).label('D3', loc='bottom', ofst=0.05)
        elm.Diode().at(bot).theta(45).length(side).label('D4', loc='bottom', ofst=0.05)
        text((xa + h, ya), 'D_Mosyagin', fs=FS - 4)
        elm.Line().at(bot).down().length(0.3)
        elm.Ground()
        # нижний вывод вторичной обмотки -> узел b (провод в обход моста снизу)
        yb = bot[1] - 0.9
        elm.Line().at(s2).down().toy(yb)
        elm.Line().right().tox(xb + 0.8)
        elm.Line().up().toy(ya)
        elm.Line().left().tox(xb)
        node((xb + 0.45, ya), 'b', loc='top', ofst=0.12)
        # верхняя вершина -> фильтр и нагрузка
        y_bus = top[1] + 0.45
        elm.Line().at(top).up().toy(y_bus)
        L = elm.Line().right().tox(xb + 1.9)
        node((xb + 1.0, y_bus), 'f' if stab else 'out')
        x_c = L.end[0]
        hh = y_bus - bot[1] + 0.3
        capacitor(x_c, y_bus, hh)
        if stab:
            stabilizer_and_load(x_c, y_bus, hh)
        else:
            load_only(x_c, y_bus, hh)
        return d


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    for name, fn, st in [('sch_hw', halfwave, False), ('sch_hw_stab', halfwave, True),
                         ('sch_br', bridge, False), ('sch_br_stab', bridge, True)]:
        d = fn(st)
        d.save(f'{out}/{name}.png', dpi=200)
        print('saved', name)
