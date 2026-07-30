#!/usr/bin/env python3
import ast
import json
import j2735_202409
import socket
import threading

# Global variables
_send_sock = None
_send_sock_lock = threading.Lock()
_send_dest = None

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
        "BSM":  "0x20",
        "SRM":  "0xE0000016",
        "SDSM": "0x8010"
    }
    return mapping.get(msg_type, "0x00000000") # Default to 0 if unknown

def build_amf(payload: str, msg_type: str) -> str:
    """Build AMF string with given payload.
    
    Args:
        payload: The message payload as a hex string.
        msg_type: The type of message (e.g. "SRM", "SDSM").
        psid: The PSID for the message.
    Returns:
        The complete AMF string.
    """
    fields = {
        "Version":       "0.7",
        "Type":          msg_type,
        "PSID":          map_msg_type_to_psid(msg_type),
        "Priority":      "2",
        "TxMode":        "CONT",
        "TxChannel":     "183",
        "TxInterval":    "0",
        "DeliveryStart": "",
        "DeliveryStop":  "",
        "Signature":     "False",
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