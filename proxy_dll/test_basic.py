"""Test: send a small message and read response character by character."""
import socket
import time

s = socket.socket()
s.settimeout(5)
s.connect(("127.0.0.1", 9876))
print("Connected")

# Send minimal status command
msg = b'{"cmd":"status"}\n'
print(f"Sending: {msg}")
s.sendall(msg)
time.sleep(0.5)

# Try to read whatever comes back
try:
    resp = s.recv(4096)
    print(f"Received ({len(resp)} bytes): {resp!r}")
except Exception as e:
    print(f"Error receiving: {e}")

s.close()
