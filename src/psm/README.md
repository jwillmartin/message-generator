# PSM Message Generator

These scripts generate Personal Safety Messages (PSMs) for testing and development purposes.

## Trajectory Format

One new PSM will be generated for each entry in the `pos` array.

```
{
  "pos": [
    {
      "lat": 389549921,   # Latitude in microdegrees (e.g., 38.9549921°)
      "long": -771492095, # Longitude in microdegrees (e.g., -77.1492095°)
      "elevation": 30,    # Elevation in 0.1 meters (e.g., 30 means 3 meters)
      "speed": 60,        # Speed in 0.02 m/s (e.g., 60 means 1.2 m/s)
      "heading": 0        # Heading in 0.0125 degrees from North (e.g., 16320 means 204 degrees)
    }
  ]
}
```

## Usage

1. Edit the `psmTrajectory.json` file to specify the desired trajectory for the PSM messages.
2. Run the `generate-psm.py` script to create the PSM messages based on the specified trajectory.
