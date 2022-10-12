# ForzaGUI

GUI application for realtime display of telemetry and derived statistics and graphs for Forza Horizon 5

This was a project never originally intended for public view, a hobby project for getting back to Python programming. Code quality is all over the place depending on when the function was written or updated. The GUI seems to be functional on Windows only.

There are various 'plugins' that offer telemetry readouts or derivations but may not be readily enabled unless the code responsible for placing the frames is updated. The plugins that are not currently active may not function or cause performance degradation.

Current focus is on making an accurate shiftled display. Work has been put into deriving information for an accurate progression of speed over time per gear, this will be used to derive more accurate triggers on rpm values to progress LED states. See dragderivation.py for various methods to derive top speeds, speed over time, and the impact of drag on modified engine torque. This applies to the torque value after multiplying with the gear ratio and multiplying the speed to match the ratio.

Examples of telemetry displayed, derived numbers and graphs:
- acceleration, brake, steering input
- car ordinal, PI, drivetrain, min/max/idle rpm
- derived peak power, torque, rev limit
- slip ratio visualized per wheel (longitudinal and lateral)
- absolute suspension values per wheel: min/max/avg/current
- launch statistics: 0 to 97kmh, 0 to 161 km/h and 100 to 200 km/h and ability to dump the data
- lateral G statistics: per X, Y, Z axis and total vector length, per frame or averaged over 300 frames with ability to dump the data
- brake statistics: start to end speed, distance and duration with ability to dump the data
- transmission statistics: per-gear ratio (no effective way to derive final ratio), duration of power cut (excludes clutch behavior)
- torque-per-gear graph: after collecting a full rpm sweep at moderate speed with per-gear ratio

Basic steps for torque graph:
- Note that the GUI only updates after Collect Data or F10 is pressed
- Collect gear ratios with F9
- F9 again to stop updating ratios during data collection for torque
- set car to a drag strip and select gear for several seconds of data collection (3rd or 4th is usually fine)
- Press F8 and press W for instant 100% forward acceleration
- Hold W until rev limit is hit
- click on RPM/Torque (f8) button to display graph

As the port is hardcoded to 12350, set remote telemetry in FH5 to 127.0.0.1 and port 12350.

Original code by https://github.com/Juice-XIJ/forza_auto_gear

![example GUI](example.png)
![example torque graph per gear](example_AcuraNSX_stock.png)
![example drag corrected torque per gear](drag_corrected_torque_AcuraNSX_stock.png)
![example derived speed over time per gear](speed_per_gear_AcuraNSX_stock.png)
