#!/usr/bin/python3
import os, sys
from time import sleep

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helper

def build_bsm(pos: dict) -> str:
    """Build BSM dictionary with mandatory fields. Returns a string."""
    cnt = helper.next_msg_cnt()

    bsm_id = bytes.fromhex("597f0d67")
    
    bsm = {
        "messageId": 20,
        "value": (
            "BasicSafetyMessage",
            {
                "coreData": {
                    "msgCnt": cnt,
                    "id": bsm_id,
                    "secMark": helper.get_sec_mark(),
                    "lat": pos["lat"],
                    "long": pos["long"],
                    "elev": pos["elevation"],
                    "accuracy": 
                    {
                        "semiMajor": 255,
                        "semiMinor": 255,
                        "orientation": 65535
                    },
                    "transmission": "unavailable",
                    "speed": 0,
                    "heading": pos["heading"],
                    "angle": 127,
                    "accelSet": {
                        "long": 0,
                        "lat": 2000,
                        "vert": 1,
                        "yaw": 0
                    },
                    "brakes": {
                    "wheelBrakes": (0, 5),
                    "traction": "unavailable",
                    "abs": "unavailable",
                    "scs": "unavailable",
                    "brakeBoost": "unavailable",
                    "auxBrakes": "unavailable"
                    },
                    "size": {
                    "width": 50,
                    "length": 50
                    }
                },
                "partII": [
                {
                    "partII-Id": 2,
                    "partII-Value": (
                        "SupplementalVehicleExtensions",
                        {
                            "classification": 82,
                            "classDetails": {
                                "keyType": 82
                            }
                        }
                    )
                }
                ]
            }
        )
    }

    return str(bsm)

def main():
    path_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bsmTrajectory.json")
    path = helper.load_path(path_file)
    for pos in path["pos"]:
        bsm_str = build_bsm(pos=pos)
        frame = helper.make_message_frame(bsm_str)
        uper = frame.to_uper()
        print(uper.hex())
        helper.send_message(msg=uper, ip_send="127.0.0.1", port_send=1516)
        sleep(0.5)

if __name__ == "__main__":
    main()
