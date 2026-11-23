#!/usr/bin/env python3
import os
import sys
from time import sleep

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helper

def build_psm(pos: dict) -> str:
    """Build PSM dictionary with mandatory fields. Returns a string.

    Args:
        pos: Path entry with "lat", "long", "elevation", "speed", and "heading".

    Returns:
        A string representation of the PSM dictionary.
    """
    cnt = helper.next_msg_cnt()

    psm_id = bytes.fromhex("597f0d67")

    psm = {
        "messageId": 32,
        "value": (
            "PersonalSafetyMessage",
            {
                "basicType": "aPEDESTRIAN",
                "secMark": helper.get_sec_mark(),
                "msgCnt": cnt,
                "id": psm_id,
                "position": {
                    "lat": pos["lat"],
                    "long": pos["long"],
                    "elevation": pos["elevation"]
                },
                "accuracy": {
                    "semiMajor": 255,
                    "semiMinor": 255,
                    "orientation": 65535
                },
                "speed": pos["speed"],
                "heading": pos["heading"]
            }
        )
    }

    return str(psm)

def main():
    path_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "psmTrajectory.json")
    path = helper.load_path(path_file)
    for pos in path["pos"]:
        psm_str = build_psm(pos=pos)
        frame = helper.make_message_frame(psm_str)
        uper = frame.to_uper()
        print(uper.hex())
        helper.send_message(msg=uper, ip_send="127.0.0.1", port_send=1516)
        sleep(0.5)

if __name__ == "__main__":
    main()
