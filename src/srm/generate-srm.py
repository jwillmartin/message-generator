#!/usr/bin/python3
import datetime
import threading
import json
import j2735_202409
import socket
from time import sleep

# Global variables
msgCnt = 0
msgCnt_lock = threading.Lock()
_send_sock = None
_send_sock_lock = threading.Lock()
_send_dest = None

def buildSRM():
    """Build SRM dictionary with mandatory fields. Returns a string."""
    global msgCnt
    with msgCnt_lock:
        cnt = msgCnt
        msgCnt = (msgCnt + 1) & 0x7F # msgCnt is 0-127 (wrap at 128)

    entityId = "40322472"

    srm = {
        "messageId": 29,
        "value": {
        "timeStamp": getMOY(),
        "second": getDSecond(),
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
            "minute": getMOY(),
            "second": getETA(),
            "duration": 10000
            }
        ],
        "requestor": {
            "id": {
            "entityID": entityId
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

def buildAMF(payload: str) -> str:
    """Build AMF string with given payload."""
    amf = """
        Version=0.7
        Type=SRM
        PSID=0xE0000016
        Priority=2
        TxMode=CONT
        TxChannel=183
        TxInterval=0
        DeliveryStart=
        DeliveryStop=
        Signature=False
        Encryption=False
        Payload="""
    amf += payload
    print(f"AMF: {amf}")
    return amf

def getMOY() -> int:
    """Get estimated future minute of year."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    start_of_year = datetime.datetime(now.year, 1, 1, tzinfo=datetime.timezone.utc)
    delta = now - start_of_year
    moy = delta.days * 1440 + now.hour * 60 + now.minute
    if getDSecond() + 10000 >= 60000:
        moy += 1
    return moy

def getDSecond() -> int:
    """Get millisecond of current minute."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    dsecond = now.second * 1000 + now.microsecond // 1000
    return dsecond

def getETA() -> int:
    """Return a 10 second estimated time of arrival in milliseconds of the current minute."""
    DSecond = getDSecond()
    if DSecond + 10000 >= 60000:
        eta = (DSecond + 10000) - 60000
    else:
        eta = DSecond + 10000
    return eta

def sendMessage(msg: bytes, ip_send: str = "10.199.1.208", port_send: int = 1516) -> None:
    """Send a UDP message, using a cached socket."""
    global _send_sock, _send_dest
    try:
        with _send_sock_lock:
            if _send_dest != (ip_send, port_send) or _send_sock is None:
                if _send_sock:
                    _send_sock.close()
                _send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                _send_sock.connect((ip_send, port_send))
                _send_dest = (ip_send, port_send)
            sock = _send_sock
        sock.send(msg)
    except Exception as e:
        print(f"Error in send function: {e}")

def main() -> None:
    """Main function to build and encode SRM message."""
    frame = j2735_202409.MessageFrame.MessageFrame
    i = 0
    # Send 2 messages with a 1 second delay to ensure different timestamps and message counts
    while i < 2:
        srm_str = buildSRM()
        frame.from_jer(srm_str)
        uper = frame.to_uper()
        amf = buildAMF(uper.hex())
        sendMessage(amf.encode('utf-8'))
        i += 1
        sleep(1)

if __name__ == "__main__":
    main()
