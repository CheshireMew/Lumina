import requests
import os
import json
import time

BASE_URL = "http://127.0.0.1:8010/lumina/chat"

def test_session_persistence():
    user_id = "tester_123"
    char_id = "hiyori"
    payload = {
        "user_input": "My favorite color is Blue.",
        "user_id": user_id,
        "character_id": char_id
    }

    print(f"--- Sending Step 1: Telling AI favorite color ---")
    response = requests.post(f"{BASE_URL}/completions", json=payload)
    if response.status_code == 200:
        print("Success: Message sent.")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return

    # Check if file exists - Backend uses relative path 'data/sessions' from its CWD
    # We should look in the project root if backend is run from there.
    session_file = f"python_backend/data/sessions/{char_id}_{user_id}.json"
    if not os.path.exists(session_file):
        # Try without python_backend prefix if script is run from project root, 
        # but backend might have created it in its own subfolder if CWD was python_backend.
        # Let's check both or just rely on the script being in project root.
        session_file = f"data/sessions/{char_id}_{user_id}.json"
    if os.path.exists(session_file):
        print(f"Success: Session file found at {session_file}")
        with open(session_file, "r") as f:
            data = json.load(f)
            history = data.get("short_term_history", [])
            print(f"History length: {len(history)}")
    else:
        print(f"Error: Session file NOT found at {session_file}")
        return

    print("\n--- Sending Step 2: Asking AI what is my favorite color ---")
    payload2 = {
        "user_input": "What is my favorite color?",
        "user_id": user_id,
        "character_id": char_id
    }
    response2 = requests.post(f"{BASE_URL}/chat/completions", json=payload2)
    if response2.status_code == 200:
        # Since it's a stream (usually), we might need to parse or just check the result if it was a blocking call.
        # But wait, our /chat/completions mentioned it returns a stream if stream=True, 
        # but in logic it might be returning a response.
        print("AI Responded. Check logs for content if streaming.")
        # Let's check the history file again
        with open(session_file, "r") as f:
            data = json.load(f)
            history = data.get("short_term_history", [])
            print(f"History length after 2nd turn: {len(history)}")
            for msg in history:
                print(f"  {msg['role']}: {msg['content'][:50]}...")
    else:
        print(f"Error: {response2.status_code}")

if __name__ == "__main__":
    test_session_persistence()
