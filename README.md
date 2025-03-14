Usage:
The script must be run with exactly the 2 following arguments (in this order):
-path to the map file
-path to the json file containing cell profiles and additional settings
  example (valid for the offered demo settings):
  python main.py example.map config.json

Additional details:
Exacly one entrance and exactly one exit are expected. These must be defined in the settings file.
The map must be rectangular. Larger maps impact performance but are still supported.
Any amount of cell types is supported, but larger amounts will somewhat impact performance.
The map may contain empty lines and comments (lines starting with #). These will be fully ignored when the map is loaded
