"""Общие вещи для скриптов: каталог прогонов ngspice и чтение бинарных raw-файлов."""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, 'runs')
os.makedirs(RUNS, exist_ok=True)


def read_raw(path):
    """Бинарный raw-файл ngspice -> словарь {имя вектора: numpy-массив}."""
    with open(path, 'rb') as f:
        data = f.read()
    head, _, body = data.partition(b'Binary:\n')
    lines = head.decode('latin-1').splitlines()
    nvar = int(next(l for l in lines if l.startswith('No. Variables')).split(':')[1])
    npts = int(next(l for l in lines if l.startswith('No. Points')).split(':')[1])
    i0 = lines.index('Variables:') + 1
    names = [lines[i0 + k].split()[1].lower() for k in range(nvar)]
    arr = np.frombuffer(body[:8 * nvar * npts], dtype='<f8').reshape(npts, nvar)
    return {n: arr[:, k].copy() for k, n in enumerate(names)}
