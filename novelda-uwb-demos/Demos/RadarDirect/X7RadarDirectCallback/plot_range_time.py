rt = x[:,0,0,:]

plt.imshow(
    rt.T,
    aspect="auto",
    origin="lower",
    cmap="jet"
)

plt.xlabel("Frame")
plt.ylabel("Range Bin")
plt.colorbar()
plt.show()