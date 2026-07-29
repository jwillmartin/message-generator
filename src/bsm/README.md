# BSM Message Generator

These scripts generate Basic Safety Messages (BSMs) for testing and development purposes.

## Trajectory Format

One new BSM will be generated for each entry in the `pos` array.

```
{
  "pos": [
    {
      "lat": 389549921,
      "long": -771492095,
      "elevation": 30,
      "heading": 0
    }
  ]
}
```

## Usage

1. Edit the `bsmTrajectory.json` file to specify the desired trajectory for the BSM messages.
2. Run the `generate-bsm.py` script to create the BSM messages based on the specified trajectory.
