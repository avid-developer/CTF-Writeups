#!/usr/bin/env python3
import subprocess
import socket
import time

# Target server info
TARGET_HOST = "kashictf.iitbhucybersec.in"
TARGET_PORT = 39900

# Original parameters provided by the challenge
original_data = "count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt"
appended_data = "&file=flag.txt"
original_hmac = "01be4a249bed4886b93d380daba91eb4a0b1ee29"

# Adjust these key length bounds as necessary
KEY_MIN = 5
KEY_MAX = 51  # will try key lengths 5 through 50

print("Starting bruteforce over key lengths from", KEY_MIN, "to", KEY_MAX-1)
for key_len in range(KEY_MIN, KEY_MAX):
    print(f"\n[*] Trying key length: {key_len}")
    
    # Construct the hashpump command
    # The command will output two lines:
    # Line 1: New signature
    # Line 2: New forged data (which includes the necessary padding)
    cmd = [
        "./HashPump/hashpump",
        "-s", original_hmac,
        "-d", original_data,
        "-a", appended_data,
        "-k", str(key_len)
    ]
    
    try:
        result = subprocess.check_output(cmd).decode("utf-8")
    except subprocess.CalledProcessError as e:
        print(f"[!] hashpump failed for key length {key_len}: {e}")
        continue

    lines = result.strip().splitlines()
    if len(lines) < 2:
        print("[!] Unexpected hashpump output:", result)
        continue

    new_signature = lines[0].strip()
    new_data = lines[1].strip()

    # Build the final payload to send, using the format: data|hmac
    forged_payload = f"{new_data}|{new_signature}"
    print(f"[*] Forged payload for key length {key_len}:")
    print(forged_payload)
    
    # Connect to the target server and send the payload
    try:
        with socket.create_connection((TARGET_HOST, TARGET_PORT), timeout=5) as s:
            s.sendall(forged_payload.encode("latin-1"))
            response = s.recv(4096).decode("utf-8", errors="replace")
            print("[*] Server response:")
            print(response)
            # If the response seems to contain the flag, stop iterating.
            if "KashiCTF{" in response.lower():
                print("\n[+] Flag found!")
                break
    except Exception as ex:
        print(f"[!] Error connecting to server for key length {key_len}: {ex}")
    
    # Wait a bit before trying the next key length
    time.sleep(1)