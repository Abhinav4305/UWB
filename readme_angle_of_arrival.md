# Angle of Arrival & Directional Gesture Detection

This document explains the physical and mathematical mechanisms that allow the X7 UWB (Ultra-Wideband) radar to determine the exact direction of a hand gesture (e.g., Left-to-Right vs. Right-to-Left, or Up-to-Down).

## 1. The Hardware: 2x2 MIMO Antennas
A single radar antenna can only tell you the *distance* of an object, not its direction. To figure out whether a hand is moving left, right, up, or down, the X7 radar utilizes a **MIMO (Multiple-Input Multiple-Output)** antenna array.

Specifically, it uses:
- **2 Transmit (TX) Antennas**
- **2 Receive (RX) Antennas**

By rapidly alternating which antenna is transmitting and receiving, the radar creates **4 "Virtual" Antennas** (`2 TX × 2 RX`). Because these antennas are physically separated by a few millimeters on the silicon chip, they each "see" the room from a slightly different angle.

## 2. The Data: Complex I/Q Signals
The radar does not just give us a standard real number for the reflection strength. It gives us **Complex I/Q (In-phase and Quadrature)** data.
Mathematically, this is represented as a complex number: `I + jQ`.

From this complex number, we can calculate two things:
1. **Amplitude (Magnitude):** How strong the reflection is (tells us how large the hand is).
2. **Phase (Angle):** The exact sub-millimeter position of the hand within the radar wave.

## 3. The Physics: Phase Interferometry
When you swipe your hand from **Left to Right**:
1. The radar wave bounces off your hand and travels back to the sensor.
2. Because your hand is on the left side of the chip, the reflected wave hits the **Left RX Antenna** a fraction of a picosecond *before* it hits the **Right RX Antenna**.
3. This microscopic time delay causes a **Phase Shift** between the I/Q signals recorded by the left and right antennas. 

Conversely, if you swipe from **Up to Down**, the phase shift occurs across the vertical axis of the virtual antennas. By measuring the phase differences between all 4 virtual antennas, the system can calculate the exact 3D Angle of Arrival (AoA) of the hand.

## 4. The Brain: Convolutional Neural Networks (CNN)
In traditional radar engineering, calculating the Angle of Arrival requires complex trigonometry algorithms (like MUSIC or ESPRIT). 

However, in our pipeline, we skip the manual math entirely. During data collection, we extract a 4-dimensional matrix of shape:
`[Time (Frames), TX Antennas, RX Antennas, Range Bins]`
*(e.g., `[64, 2, 2, 34]`)*

We feed these raw complex matrices directly into a **Convolutional Neural Network (CNN)**. Over the course of training, the CNN's filters automatically learn to recognize the specific Phase Shift patterns that correspond to a Left-to-Right swipe versus a Right-to-Left swipe, resulting in highly robust directional gesture detection!
