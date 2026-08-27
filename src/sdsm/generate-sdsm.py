#!/usr/bin/env python3
import os
import sys
import threading
from time import sleep
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helper

# Global variables
msgCnt = 0
msgCnt_lock = threading.Lock()

def build_sdsm(ref_pos: dict, pos: dict) -> str:
    """Build SDSM dictionary with mandatory fields. Returns a string.

    Args:
        ref_pos: Reference position with "lat", "long", and "elevation".
        pos: Object entry with "offsetX", "offsetY", "speed", and "heading".

    Returns:
        A string representation of the SDSM dictionary.
            """
    global msgCnt
    with msgCnt_lock:
        cnt = msgCnt
        msgCnt = (msgCnt + 1) & 0x7F # msgCnt is 0-127 (wrap at 128)

    source_id = bytes.fromhex("010C0C0A")
    
    sdsm = {
        "messageId": 41,
        "value": (
            "SensorDataSharingMessage",
            {
            "msgCnt": cnt,
            "sourceID": source_id,
            "equipmentType": "rsu",
            "sDSMTimeStamp": {
                "year": int(get_current_timestamp()['year']),
                "month": int(get_current_timestamp()['month']),
                "day": int(get_current_timestamp()['day']),
                "hour": int(get_current_timestamp()['hour']),
                "minute": int(get_current_timestamp()['minute']),
                "second": int(get_current_timestamp()['second'])
            },
            "refPos": {
                "lat": ref_pos["lat"],
                "long": ref_pos["long"],
                "elevation": ref_pos["elevation"]
            },
            "refPosXYConf": {
                "semiMajor": 255,
                "semiMinor": 255,
                "orientation": 65535
            },
            "objects": []
            }
        )
        }

    obj = {
        "detObjCommon": {
            "objType": "vru",
            "objTypeCfd": 98,
            "objectID": 27116,
            "measurementTime": 10,
            "timeConfidence": "time-000-100",
            "pos": {
                "offsetX": pos["offsetX"],
                "offsetY": pos["offsetY"]
            },
            "posConfidence": {
                "pos": "a20cm",
                "elevation": "elev-000-20"
            },
            "speed": pos["speed"],
            "speedConfidence": "prec0-1ms",
            "heading": pos["heading"],
            "headingConf": "prec0-05deg"
        },
        "detObjOptData": (
            "detVRU",
            {
                "basicType": "aPEDESTRIAN",
                "propulsion": ("human", "onFoot")
            }
        )
    }
    sdsm["value"][1]["objects"].append(obj)

    return str(sdsm)

def get_current_timestamp():
    """Generate the current timestamp as a dictionary."""
    now = datetime.now(tz=timezone.utc)
    return {
        'year': now.year,
        'month': f"{now.month:02d}",
        'day': f"{now.day:02d}",
        'hour': f"{now.hour:02d}",
        'minute': f"{now.minute:02d}",
        'second': f"{now.second:02d}",
    }

def main():
    path_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdsmTrajectory.json")
    path = helper.load_path(path_file)
    for pos in path["pos"]:
        sdsm_str = build_sdsm(ref_pos=path["refPos"], pos=pos)
        frame = helper.make_message_frame(sdsm_str)
        uper = frame.to_uper()
        amf = helper.build_amf(uper.hex(), "SDSM", signature=True)
        helper.send_message(msg=amf.encode(), ip_send="192.168.55.72", port_send=1516)
        sleep(0.1)  # Sleep for 100ms between messages

if __name__ == "__main__":
    main()
