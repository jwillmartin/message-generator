# SDSM Message Generator

These scripts generate Sensor Data Sharing Messages (SDSMs) for testing and development purposes.

## Trajectory Format

One new SDSM will be generated for each entry in the `pos` array. The `refPos` object specifies the reference position, while each entry in the `pos` array specifies the offset from the reference position, speed, and heading.

```
{
  "refPos": {
    "lat": 389549921,   # Latitude in microdegrees (e.g., 38.9549921°)
    "long": -771492095, # Longitude in microdegrees (e.g., -77.1492095°)
    "elevation": 30     # Elevation in 0.1 meters (e.g., 30 means 3 meters)
  },
  "pos": [
    {
      "offsetX": 32767, # Offset in 0.1 meters (e.g., 32767 means 3276.7 meters)
      "offsetY": 32767, # Offset in 0.1 meters (e.g., 32767 means 3276.7 meters)
      "speed": 100,     # Speed in 0.02 m/s (e.g., 100 means 2 m/s)
      "heading": 16320  # Heading in 0.0125 degrees from North (e.g., 16320 means 204 degrees)
    }
  ]
}
```

## Usage

1. Edit the `sdsmTrajectory.json` file to specify the desired trajectory for the SDSM messages.
2. Run the `sdsmSim.py` script to create the SDSM messages based on the specified trajectory.
