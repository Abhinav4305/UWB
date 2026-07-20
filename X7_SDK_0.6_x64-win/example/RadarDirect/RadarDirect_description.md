# Novelda Radar Direct

The Novelda Radar Direct example is made to be used with a Nordic nRF52840DK with a X7-shield. 
For information on how to build and flash the example project, see the README-file. 

## Output

The output should look similar to this:

```
BALog(1): Loading app version: x.y.z
BALog(1): App loaded.
BALog(0): RadarSource::BuildUp
Got output of size: 2224 bytes
    [ 0x00 0x00 0x03 ]
  Frame info: sequence_number=0 timestamp=1720187559768
Got output of size: 1768 bytes
    [ 0x00 0x01 0x03 ]
  Frame info: sequence_number=101 timestamp=1720187559969
```

Each radar frame console message indicates a radar frame arriving in
`radar_direct_process_output()`, by default the number of frames per second (FPS) is
configured to 250.0. It's also explicitly set to 250.0 in `main()` to demonstrate
how it can be set programmatically.