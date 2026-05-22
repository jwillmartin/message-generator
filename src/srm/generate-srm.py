#!/usr/bin/env python3
import datetime
import os
import sys
import threading
import json
import j2735_202409
from time import sleep

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helper

# Global variables
msgCnt = 0
msgCnt_lock = threading.Lock()

def build_srm():
    """Build SRM dictionary with mandatory fields. Returns a string."""
    global msgCnt
    with msgCnt_lock:
        cnt = msgCnt
        msgCnt = (msgCnt + 1) & 0x7F # msgCnt is 0-127 (wrap at 128)

    entity_id = "40322472"

    srm = {
        "messageId": 29,
        "value": {
        "timeStamp": get_moy(),
        "second": get_dsecond(),
        "sequenceNumber": cnt,
        "requests": [
            {
            "request": {
            "id": {
            "id": 13558 # intersectionId
            },
            "requestID": 1,
            "requestType": "priorityRequest",
            "inBoundLane": {
            "lane": 1
            }
            },
            "minute": get_moy(),
            "second": get_eta(),
            "duration": 10000
            }
        ],
        "requestor": {
            "id": {
            "entityID": entity_id
            },
            "type": {
            "role": "transit" # transit or fire
            },
            "position": {
            "position": {
            "lat": 389562674,
            "long": -771505027,
            "elevation": 40
            },
            "heading": 0,
            "speed": {
            "transmisson": "unavailable",
            "speed": 415
            }
            }
        }
        }
        }

    return json.dumps(srm)

def get_moy() -> int:
    """Get estimated future minute of year."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    start_of_year = datetime.datetime(now.year, 1, 1, tzinfo=datetime.timezone.utc)
    delta = now - start_of_year
    moy = delta.days * 1440 + now.hour * 60 + now.minute
    if get_dsecond() + 10000 >= 60000:
        moy += 1
    return moy

def get_dsecond() -> int:
    """Get millisecond of current minute."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    dsecond = now.second * 1000 + now.microsecond // 1000
    return dsecond

def get_eta() -> int:
    """Return a 10 second estimated time of arrival in milliseconds of the current minute."""
    dsecond = get_dsecond()
    if dsecond + 10000 >= 60000:
        eta = (dsecond + 10000) - 60000
    else:
        eta = dsecond + 10000
    return eta

def main() -> None:
    """Main function to build and encode SRM message."""
    frame = j2735_202409.MessageFrame.MessageFrame

    # Send 2 messages with a 1 second delay to ensure different timestamps and message counts
    i = 0
    while i < 2:
        srm_str = build_srm()
        frame.from_jer(srm_str)
        uper = frame.to_uper()
        amf = helper.build_amf(payload=uper.hex(), msg_type="SRM")
        helper.send_message(msg=amf.encode('utf-8'), ip_send="127.0.0.1", port_send=1516)
        i += 1
        sleep(1)

if __name__ == "__main__":
    main()
