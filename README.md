# message-generator
Generates SAE J2735 V2X Messages

## Prerequisites

- python >=3.8
- j2735_202409

Run the [install.sh](/install/install.sh) script to install all dependencies.
```bash
cd install
./install.sh
```

## Usage

Each folder in the `src` directory contains a script that generates a specific type of message. For example, to generate a SDSM message, run the following command:
```bash
./sdsmSim.py
```