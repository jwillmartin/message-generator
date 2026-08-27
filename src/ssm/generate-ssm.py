#!/usr/bin/env python3
import os
import sys
import json
from time import sleep

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helper

def build_ssm():
    """Build SSM dictionary with mandatory fields. Returns a string."""
    cnt = helper.next_msg_cnt()

    entity_id = "40322472"

    ssm = {
        'messageId': 30,
        'value': {
            'timeStamp': helper.get_moy(),
            'second': helper.get_dsecond(),
            'sequenceNumber': cnt,
            'status': [
                {
                'sequenceNumber': cnt,
                'id': {
                'id': 103 # intersectionId
                },
                'sigStatus': [
                    {
                    'requester': {
                        'id': {
                        'entityID': entity_id
                        },
                        'request': 16,
                        'sequenceNumber': cnt,
                        'role': 'transit'
                    }, 
                    'inboundOn': {
                    'lane': 7
                    }, 
                    'outboundOn': {
                    'lane': 15
                    },
                    'minute': helper.get_moy(),
                    'second': helper.get_eta(),
                    'duration': 10000,
                    'status': 'rejected' # requested, processing, watchOtherTraffic, granted, rejected, maxPresense, reserviceLocked
                    }
                ]
                }
            ]
        }
    }

    return json.dumps(ssm)

def main() -> None:
    """Main function to build and encode SSM message."""
    # Send 2 messages with a 1 second delay to ensure different timestamps and message counts
    i = 0
    while i < 2:
        ssm_str = build_ssm()
        frame = helper.make_message_frame_jer(ssm_str)
        uper = frame.to_uper()
        amf = helper.build_amf(payload=uper.hex(), msg_type="SSM")
        helper.send_message(msg=amf.encode('utf-8'), ip_send="127.0.0.1", port_send=1516)
        i += 1
        sleep(1)

if __name__ == "__main__":
    main()
