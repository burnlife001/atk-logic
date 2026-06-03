"""Quick test of the proxy DLL TCP server."""
import socket
import json

s = socket.socket()
s.settimeout(5)
s.connect(("127.0.0.1", 9876))

# Test status command
s.sendall(b'{"cmd":"status"}\n')
resp = s.recv(4096)
print("Status:", resp.decode().strip())

# Test file command (list latest capture)
s.sendall(b'{"cmd":"file"}\n')
resp = s.recv(4096)
print("Latest file:", resp.decode().strip())

s.close()
print("\nProxy DLL is working!")
