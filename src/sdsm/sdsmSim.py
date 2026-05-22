#!/usr/bin/env python3
from datetime import datetime
import os
import sys
import threading, ast
import j2735_202409

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helper

# Global variables
msgCnt = 0
msgCnt_lock = threading.Lock()

def build_sdsm(num_objs: int) -> str:
    """Build SDSM dictionary with mandatory fields. Returns a string.
    
    Args:
        num_objs: The number of objects to include in the message.
    
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
                "lat": 389549921,
                "long": -771492095,
                "elevation": 30
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

    # Build one detObjCommon per object
    for i in range(num_objs):
        obj = {
            "detObjCommon": {
                "objType": "vru",
                "objTypeCfd": 98,
                "objectID": 27116 + i,
                "measurementTime": 10,
                "timeConfidence": "time-000-100",
                "pos": {
                    "offsetX": 32767,
                    "offsetY": 32767
                },
                "posConfidence": {
                    "pos": "a20cm",
                    "elevation": "elev-000-20"
                },
                "speed": 100,
                "speedConfidence": "prec0-1ms",
                "heading": 16320,
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
    now = datetime.now()
    return {
        'year': now.year,
        'month': f"{now.month:02d}",
        'day': f"{now.day:02d}",
        'hour': f"{now.hour:02d}",
        'minute': f"{now.minute:02d}",
        'second': f"{now.second:02d}",
    }

def make_message_frame(sdsm):
    msg = ast.literal_eval(sdsm)
    frame = j2735_202409.MessageFrame.MessageFrame
    frame.set_val(msg)
    return frame

def main():
    sdsm_str = build_sdsm(num_objs=1)
    frame = make_message_frame(sdsm_str)
    uper = frame.to_uper()
    amf = helper.build_amf(payload=uper.hex(), msg_type="SDSM")
    helper.send_message(msg=amf.encode('utf-8'), ip_send="127.0.0.1", port_send=1516)


if __name__ == "__main__":
    main()
