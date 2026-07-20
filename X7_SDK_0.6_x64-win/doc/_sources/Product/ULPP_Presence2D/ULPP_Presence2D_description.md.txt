# Novelda ULPP Presence 2D

The Novelda ULPP Presence 2D example is made to be used with a Nordic nRF52840DK with a X7-shield. 
For information on how to build and flash the example project, see the README-file. 

## Output

The output should look similar to this:

```
BALog(1): Loading app version: x.y.z
BALog(1): App loaded.
BALog(0): RadarSource::BuildUp
Sequence number: 1 Timestamp: 1280 Data: [ Presence: 0, Position (cm): (   4,  -5), Confidence: 070 ]
Sequence number: 3 Timestamp: 1405 Data: [ Presence: 1, Position (cm): (   4,  -5), Confidence: 091 ]
Sequence number: 5 Timestamp: 1530 Data: [ Presence: 1, Position (cm): (   4,  -5), Confidence: 097 ]
```

The Human presence raw data in the output consists of the following information: [a, b, c, d]

* a = Presence (001) / No Presence (000) inside the given detection zone
* b = X-position of the closest target (in cm)
* c = Y-position of the closest target (in cm)
* d = Confidence value (000-100)

The Human detection 2D raw data is a dynamic length output of shape Nx5, where N is the number of detections.
The number N is limited by the two parameters `max_num_detections` and `max_num_human_detection_2d_outputs` described below.

The fields related to each detection is: [a, b, c, d, e]

* a = Inside state - whether the detection is inside the detection zone (1) or outside (0)
* b = X-position of the detection (in m)
* c = Y-position of the detection (in m)
* d = Signal power of the detection (in linear scale)
* e = Noise power of the detection (in linear scale)

## Default settings

```
    .detection_zone_xy_points = (const float[]){0.0f, 0.5f, 1.0f, 0.5f, 1.0f, -0.5f, 0.0f, -0.5f},
    .detection_zone_xy_points_length = 8,
    .threshold_level_adjustment_linear = 1.0f,
    .confidence_values = {30, 80, 75, 25},
    .max_num_detections = 1,
    .max_num_human_detection_2d_outputs = 0
```

## Description of settings

`detection_zone_xy_points` is a vector consisting of X and Y coordinates (in meters) defining the detection zone. 
The default zone is a square with four points and is configured like this: {X1, Y1, X2, Y2, X3, Y3, X4, Y4}.
The X-axis is straight out in the room from the middle of the sensor. The Y-axis is along the length of the sensor, with 0 being in the center of the sensor module. 
The maximum size of the detection zone is 12x12 meter. Default is 1x1 meter.   

`detection_zone_xy_points_length` should be set to the total number of X and Y points. This is 8 in the default configuration. 

`threshold_level_adjustment_linear` Scalar value in linear scale which is
multiplied with the detection threshold vector to scale it up or down. To
calculate the adjustment level in dB: threshold_level_adjustment_db =
10*log<sub>10</sub>(threshold_level_adjustment_linear). Default is 1.0.

`confidence_values` is a 1x4 vector with values in the range [0-100] and consists of the following information: {a, b, c, d}

* a = Weight for Presence
* b = weight for No Presence
* c = Confidence level for Presence (confidence limit to change from No Presence -> Presence)
* d = Confidence level for No Presence (confidence limit to change from Presence -> No Presence)

A lower weight will make the application change state quicker. This is because the current detection will then be weight more than the previous ones. 
Choosing a low weight for Presence will make the detection of a user quicker, but with a potential higher risk of false positives. 
Choosing a high weight for No Presence will give lower risk of losing detection while the user is still in the zone, but will make the transition from Presence to No Presence a little slower. 
These numbers should be chosen toghether with the confidence level based on the type of application it is being used in. 

`max_num_detections` is a scalar value that specifies the maximum number of detections that is processed in the radar frame.
If enabling multiple detection outputs with the `max_num_human_detection_2d_outputs`, `max_num_detections` must be set greater than or equal to `max_num_human_detection_2d_outputs`.

`max_num_human_detection_2d_outputs` is a scalar value that specifies the maximum number of detections that will be output in the Human detection 2D message.
Increasing `max_num_human_detection_2d_outputs` beyond `max_num_detections` has no effect.

## Change configuration/settings

**Note**: After changing settings, build the project again and flash it to the board. 
The configuration of the example app can be changed in the "novelda_signalflow_app_x7.c"-file located in the "example_ULPP_Presence2D"-folder.
The ULPP configuration settings looks like this:

```
// Define the ULPP configuration
ulpp_config_t ulpp_config = {
    .detection_zone_xy_points = (const float[]){0.0f, 0.5f, 1.0f, 0.5f, 1.0f, -0.5f, 0.0f, -0.5f},
    .detection_zone_xy_points_length = 8,
    .threshold_level_adjustment_linear = 1.0f,
    .confidence_values = {30, 80, 75, 25},
    .max_num_detections = 1,
    .max_num_human_detection_2d_outputs = 0
};
```



