import numpy as np
import matplotlib.pyplot as plt

x = np.load("recording.npy")

frame = x[0,0,0,:]

plt.plot(frame)
plt.xlabel("Range Bin")
plt.ylabel("Amplitude")
plt.title("Single Radar Frame")
plt.show()