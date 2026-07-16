# Data Comparison: Why V1 Was Broken

Here is a side-by-side visual comparison of the data your neural network was training on in V1 versus the data it will train on in V2.

### ❌ The Old Data (V1)
In the old script, the radar data was accidentally mangled. Instead of 8 independent channels, it produced 4 channels. 
Notice how **two of the channels are completely blank (purple/black squares)** because the Phase information was accidentally set to zero! 
Additionally, the first and third channels are mixed together, meaning the radar had no idea if the hand was on the left or the right.

![V1 Buggy Radar Data](/C:/Users/Admin/.gemini/antigravity-ide/brain/2281aa1e-4f25-4be8-95ed-a0aeeb18cc52/v1_sample.png)

### ✅ The New Data (V2)
In the new `x7_record_v2.py` script, all 8 channels are preserved! 
- **TX0_RX0 and TX0_RX1** are the two receiving antennas. The neural network can compare these to see left/right stereo vision!
- **Real and Imag** are both captured, preserving the Doppler Phase (speed) of your hand!
- **TX1** provides a completely separate transmit angle for even more 3D spatial data.

![V2 Fixed Radar Data](/C:/Users/Admin/.gemini/antigravity-ide/brain/2281aa1e-4f25-4be8-95ed-a0aeeb18cc52/v2_sample.png)

Because the old model was looking at the top image (half blank, half blurry), it was struggling to reach high accuracy. Your new model will look at the bottom image, which gives it a crystal clear picture of the gesture!
