import urllib.request
import json
import base64
import audio_service
import interview_bridge_server

print("1. Starting bridge server and Initializing Live Session...")
interview_bridge_server.start_interview_bridge_server(8765)
interview_bridge_server.reset_live_session(
    candidate_name="Alex",
    questions=[{"text": "Tell me about yourself.", "category": "General", "difficulty": "Basic"}],
    plan_metadata={"role": "Software Engineer"}
)

state = interview_bridge_server.get_live_state()
print("Initial call stage:", state["call_stage"])
print("Initial active speaker:", state["active_speaker"])
print("Greeting subtitles:", state["subtitles"][:40])
print("Greeting audio present?", len(state["current_audio_b64"]) > 0)

print("\n2. Synthesizing test audio for candidate saying 'Yes I am ready'...")
# Generate speech for 'Yes I am ready' to simulate candidate mic input
cand_audio_bytes = audio_service.synthesize_speech("Yes I am ready")
print("Candidate speech simulated, byte count:", len(cand_audio_bytes))

cand_b64 = base64.b64encode(cand_audio_bytes).decode("utf-8")

payload = json.dumps({"audio_base64": cand_b64}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8765/speech", data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    print("Bridge /speech response:", res)

state2 = interview_bridge_server.get_live_state()
print("\n3. State after candidate said 'Yes I am ready':")
print("New call stage:", state2["call_stage"])
print("Active speaker:", state2["active_speaker"])
print("Subtitles:", state2["subtitles"][:60])
print("Syna question audio present?", len(state2["current_audio_b64"]) > 0)
