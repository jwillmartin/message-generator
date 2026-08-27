#!/usr/bin/env python3
import ast
import datetime
import json
import j2735_202409
import socket
import threading
import time

# Global variables
_send_sock = None
_send_sock_lock = threading.Lock()
_send_dest = None
_msg_cnt = 0
_msg_cnt_lock = threading.Lock()

def make_message_frame(msg_str: str):
    """Create a J2735 Message Frame using a pre-created message dictionary. 
    
    Args:
        msg_str (str): A J2735 Message dictionary, passed as a string.
    Returns:
        frame (SEQ): Message Frame Sequence of the input message dictionary."""
    msg = ast.literal_eval(msg_str)
    frame = j2735_202409.MessageFrame.MessageFrame
    frame.set_val(msg)
    return frame

def make_message_frame_jer(msg_str: str):
    """Create a J2735 Message Frame from a JER (JSON) message string.

    Args:
        msg_str (str): A J2735 Message encoded as a JER/JSON string.
    Returns:
        frame (SEQ): Message Frame Sequence of the input message.
    """
    frame = j2735_202409.MessageFrame.MessageFrame
    frame.from_jer(msg_str)
    return frame

def load_path(path_file: str) -> dict:
    """Load the reference position and object path from a JSON file.

    Args:
        path_file: Path to a JSON file containing a "refPos" dict
            {lat, long, elevation} and a "pos" list of
            {offsetX, offsetY, speed, heading} entries.

    Returns:
        The parsed JSON as a dictionary.
    """
    with open(path_file) as f:
        return json.load(f)

def map_msg_type_to_psid(msg_type: str) -> str:
    """Map message type to PSID.
    
    Args:
        msg_type: The type of message (e.g. "SRM", "SDSM").
    Returns:
        The corresponding PSID as a hex string.
    """
    mapping = {
        "BSM":    "0x20",
        "PSM":    "0x27",
        "NMEA":   "0x8001",
        "RTCM":   "0x8001",
        "SPAT":   "0x8002",
        "TIM":    "0x8003",
        "RSM":    "0x8003",
        "TAM":    "0x800F",
        "TUM":    "0x800F",
        "TUMAck": "0x800F",
        "SDSM":   "0x8010",
        "SSM":    "0xE0000015",
        "SRM":    "0xE0000016",
        "MAP":    "0xE0000017",
        "RWM":    "0xE0000019"
    }
    # Message types without an entry above fall back to the default. Add the value
    # from your deployment's PSID registry before sending them to a real device.
    return mapping.get(msg_type, "0x00000000") # Default to 0 if unknown

def build_amf(payload: str, msg_type: str, signature: bool=False) -> str:
    """Build AMF string with given payload.
    
    Args:
        payload: The message payload as a hex string.
        msg_type: The type of message (e.g. "SRM", "SDSM").
        signature: Whether the message requires a signature.
    Returns:
        The complete AMF string.
    """
    signature_str = "True" if signature else "False"
    fields = {
        "Version":       "0.7",
        "Type":          msg_type,
        "PSID":          map_msg_type_to_psid(msg_type),
        "Priority":      "3",
        "TxMode":        "CONT",
        "TxChannel":     "183",
        "TxInterval":    "0",
        "DeliveryStart": "",
        "DeliveryStop":  "",
        "Signature":     signature_str,
        "Encryption":    "False",
        "Payload":       payload,
    }
    amf = "\n".join(f"{key}={value}" for key, value in fields.items())

    print(f"AMF:\n{amf}")
    return amf

def send_message(msg: bytes, ip_send: str = "127.0.0.1", port_send: int = 1516) -> None:
    """Send a UDP message, using a cached socket.
    
    Args:
        msg: The message to send as bytes.
        ip_send: The destination IP address.
        port_send: The destination port number.
    """
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

def next_msg_cnt() -> int:
    """Return the next message count, incrementing the shared counter.

    Returns:
        The current message count, in the range 0-127 (wraps at 128).
    """
    global _msg_cnt
    with _msg_cnt_lock:
        cnt = _msg_cnt
        _msg_cnt = (_msg_cnt + 1) & 0x7F # msgCnt is 0-127 (wrap at 128)
    return cnt

def get_moy() -> int:
    """Get estimated future minute of year.

    Returns:
        The minute of the year, advanced by one if the ETA wraps into the
        next minute.
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    start_of_year = datetime.datetime(now.year, 1, 1, tzinfo=datetime.timezone.utc)
    delta = now - start_of_year
    moy = delta.days * 1440 + now.hour * 60 + now.minute
    if get_dsecond() + 10000 >= 60000:
        moy += 1
    return moy

def get_dsecond() -> int:
    """Get millisecond of current minute.

    Returns:
        The number of milliseconds elapsed in the current minute.
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    dsecond = now.second * 1000 + now.microsecond // 1000
    return dsecond

def get_eta() -> int:
    """Return a 10 second estimated time of arrival in milliseconds of the current minute.

    Returns:
        The estimated time of arrival as a millisecond of the minute.
    """
    dsecond = get_dsecond()
    if dsecond + 10000 >= 60000:
        eta = (dsecond + 10000) - 60000
    else:
        eta = dsecond + 10000
    return eta

def get_time_mark() -> int:
    """Get the current time of the hour as a J2735 TimeMark.

    Returns:
        Tenths of a second elapsed in the current hour (0-36111).
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return now.minute * 600 + now.second * 10 + now.microsecond // 100000

def get_sec_mark() -> int:
    """Generate the current secMark based on the system's time.

    Returns:
        The millisecond of the current minute, 60000-60999 during a leap
        second, or 65535 when the value is unavailable.
    """
    now = datetime.datetime.now()
    milliseconds = now.microsecond // 1000 + now.second * 1000

    # Leap second handling
    leap_second = time.gmtime().tm_sec == 60
    if leap_second:
        return 60000 + (milliseconds % 1000)  # Use range 60000-60999 for leap seconds
    elif milliseconds > 60999:
        return 65535  # Use 65535 for unavailable value
    else:
        return milliseconds

def get_current_timestamp() -> dict:
    """Generate the current UTC timestamp as a dictionary.

    Returns:
        A dictionary with "year", "month", "day", "hour", "minute", and
        "second" keys.
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return {
        'year': now.year,
        'month': f"{now.month:02d}",
        'day': f"{now.day:02d}",
        'hour': f"{now.hour:02d}",
        'minute': f"{now.minute:02d}",
        'second': f"{now.second:02d}",
    }
