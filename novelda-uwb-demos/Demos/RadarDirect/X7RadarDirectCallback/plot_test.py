import numpy as np
import matplotlib.pyplot as plt

x = np.load("rightmovement.npy")

frame = 500

plt.figure(figsize=(10,6))

plt.plot(x[frame,0,0,:], label="TX0RX0")
plt.plot(x[frame,0,1,:], label="TX0RX1")
plt.plot(x[frame,1,0,:], label="TX1RX0")
plt.plot(x[frame,1,1,:], label="TX1RX1")

plt.legend()
plt.grid()
plt.show()