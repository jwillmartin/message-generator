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

**Note:** A helper file also exists, containing various helper functions used by the message generation scripts. 
It includes an optional `build_amf` function, which adds the generated payload to an Active Message File. 
That amf string can be sent to a device for Immediate Forward, if supported. Example addition to `main()`:
```python
amf = helper.build_amf(payload=uper.hex(), msg_type="SRM")
helper.send_message(msg=amf.encode('utf-8'), ip_send="127.0.0.1", port_send=1516)
```