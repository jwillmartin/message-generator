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

def build_ssm():
    """Build SSM dictionary with mandatory fields. Returns a string."""
    global msgCnt
    with msgCnt_lock:
        cnt = msgCnt
        msgCnt = (msgCnt + 1) & 0x7F # msgCnt is 0-127 (wrap at 128)

    entity_id = "40322472"

    ssm = {
        'messageId': 30,
        'value': {
            'timeStamp': get_moy(),
            'second': get_dsecond(),
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
                    'minute': get_moy(),
                    'second': get_eta(),
                    'duration': 10000,
                    'status': 'rejected' # requested, processing, watchOtherTraffic, granted, rejected, maxPresense, reserviceLocked
                    }
                ]
                }
            ]
        }
    }

    return json.dumps(ssm)

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
    """Main function to build and encode SSM message."""
    frame = j2735_202409.MessageFrame.MessageFrame

    # Send 2 messages with a 1 second delay to ensure different timestamps and message counts
    i = 0
    while i < 2:
        ssm_str = build_ssm()
        frame.from_jer(ssm_str)
        uper = frame.to_uper()
        amf = helper.build_amf(payload=uper.hex(), msg_type="SSM")
        helper.send_message(msg=amf.encode('utf-8'), ip_send="127.0.0.1", port_send=1516)
        i += 1
        sleep(1)

if __name__ == "__main__":
    main()
