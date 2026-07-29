#!/usr/bin/python3
import os, sys
from datetime import datetime
from time import sleep
import time, threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helper

# Global variables
msgCnt = 0
msgCnt_lock = threading.Lock()

def build_bsm(pos: dict) -> str:
    """Build BSM dictionary with mandatory fields. Returns a string."""
    global msgCnt
    with msgCnt_lock:
        cnt = msgCnt
        msgCnt = (msgCnt + 1) & 0x7F # msgCnt is 0-127 (wrap at 128)

    bsm_id = bytes.fromhex("597f0d67")
    
    bsm = {
        "messageId": 20,
        "value": (
            "BasicSafetyMessage",
            {
                "coreData": {
                    "msgCnt": cnt,
                    "id": bsm_id,
                    "secMark": get_sec_mark(),
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

def get_sec_mark():
    """Generate the current secMark based on the system's time."""
    now = datetime.now()
    milliseconds = now.microsecond // 1000 + now.second * 1000

    # Leap second handling
    leap_second = time.gmtime().tm_sec == 60
    if leap_second:
        return 60000 + (milliseconds % 1000)  # Use range 60000–60999 for leap seconds
    elif milliseconds > 60999:
        return 65535  # Use 65535 for unavailable value
    else:
        return milliseconds

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
