import numpy as np
import matplotlib.pyplot as plt


with open ("settings.txt", "r") as set:
    tmp = [float(i) for i in set.read().split("\n")]

data_array = np.loadtxt("data.txt", dtype = float)
time_array = np.arange(data_array.size) / 100
voltage_array = data_array / 256 * 3.3


fig, ax = plt.subplots(figsize=(16,10), dpi = 400)
ax.plot(time_array, voltage_array, "r")

plt.xlabel("Время, с")
plt.title("Процесс заряда и разряда конденсатора в RC-цепочке")
plt.ylabel("Напряжение, В")
plt.legend("V(t)")
plt.minorticks_on()

plt.grid(which='major', color='grey', linestyle='--', linewidth = 1)
plt.grid(which='minor', color='grey', linestyle='--', linewidth = 1)

ax.set_xlim([min(time_array), 1.1*max(time_array)])
ax.set_ylim([min(voltage_array), 1.05*max(voltage_array)])

plt.text(80, 2.5, "Время заряда = 51.2 с ")
plt.text(80, 2.0, "Время разряда = 60.4 с ")

fig.savefig("graph.svg")
plt.show()

