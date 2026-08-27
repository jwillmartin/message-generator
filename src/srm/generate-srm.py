#!/usr/bin/env python3
import os
import sys
import json
from time import sleep

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helper

def build_srm():
    """Build SRM dictionary with mandatory fields. Returns a string."""
    cnt = helper.next_msg_cnt()

    entity_id = "40322472"

    srm = {
        "messageId": 29,
        "value": {
        "timeStamp": helper.get_moy(),
        "second": helper.get_dsecond(),
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
            "minute": helper.get_moy(),
            "second": helper.get_eta(),
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

def main() -> None:
    """Main function to build and encode SRM message."""
    # Send 2 messages with a 1 second delay to ensure different timestamps and message counts
    i = 0
    while i < 2:
        srm_str = build_srm()
        frame = helper.make_message_frame_jer(srm_str)
        uper = frame.to_uper()
        amf = helper.build_amf(payload=uper.hex(), msg_type="SRM")
        helper.send_message(msg=amf.encode('utf-8'), ip_send="127.0.0.1", port_send=1516)
        i += 1
        sleep(1)

if __name__ == "__main__":
    main()
