# Novelda ULPP Presence 1D

The Novelda ULPP Presence 1D example is made to be used with a X7-shield.
For information on how to build and flash the example project,
see the README-file.

## Output

The output should look similar to this:

```
BALog(1): Loading app version: x.y.z
BALog(1): App loaded.
BALog(0): RadarSource::BuildUp
Sequence number: 0 Timestamp: 1306 Data: [ Presence: 0, Range (cm): 064, Confidence: 070, Signal power: 137832 ]
Sequence number: 1 Timestamp: 1318 Data: [ Presence: 1, Range (cm): 064, Confidence: 091, Signal power: 142869 ]
Sequence number: 7 Timestamp: 2965 Data: [  ]
```

The Human presence raw data in the output consists of the following
information: [a, b, c, d, e]

* a = Presence (001) / No Presence (000) inside the given detection zone
* b = Range in cm to detection
* c = Confidence value (0-100)
* d = Signal power
* e = Radial speed in cm/s. **Note currently not in use and will always be 0.**

## Default settings

The default settings are:

```
    ulpp_config_t ulpp_config = {
        .detection_zone = { 0.5, 2.0 },
        .confidence_values = { 30, 80, 75, 25 },
        .num_mframes_per_pulse = 3,
        .threshold_level_adjustment_linear = 1.0f,
        .low_power_mode = true,
        .send_output_on_presence_change_only = true
    };
```

in novelda_signalflow_app_x7.c.

## Description of settings

`detection_zone` is a vector consisting of a start and stop value in meters

`confidence_values` is a 1x4 vector with values in the range [0-100] and
consists of the following information: {a, b, c, d}

* a = Weight for Presence
* b = weight for No Presence
* c = Confidence level for Presence
      (confidence limit to change from No Presence -> Presence)
* d = Confidence level for No Presence
      (confidence limit to change from Presence -> No Presence)

A lower weight will make the application change to the specified state faster.
This is because the current detection will then be weighted more than the
previous ones. Choosing a low weight for Presence will make the detection of a
user quicker, but with a potentially higher risk of false positives. Choosing a
high weight for No Presence will give a lower risk of losing detection while the
user is still in the zone, but will make the transition from Presence to No
Presence a little slower. These numbers should be chosen together with the
confidence level based on the type of application it is being used in.

`num_mframes_per_pulse` Number of micro frames (mframes) per pulse. Each mframe
consists of 16 range bins, each bin having a length of 0.0714 meters.
The first mframe starts at -1.145 meters.

`threshold_level_adjustment_linear` Scalar value in linear scale which is
multiplied with the detection threshold vector to scale it up or down. To
calculate the adjustment level in dB: threshold_level_adjustment_db =
10*log<sub>10</sub>(threshold_level_adjustment_linear). Default is 1.0.
