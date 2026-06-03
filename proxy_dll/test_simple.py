"""Simple test: just connect and disconnect without sending data."""
import socket
import time

s = socket.socket()
s.settimeout(5)
s.connect(("127.0.0.1", 9876))
print("Connected. Waiting 1 second without sending...")
time.sleep(1)
print("Closing...")
s.close()
print("OK - connection/disconnection worked")
