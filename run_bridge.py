import time
from interview_bridge_server import start_interview_bridge_server

start_interview_bridge_server(8765)
print("Bridge server running on port 8765")
while True:
    time.sleep(1)
