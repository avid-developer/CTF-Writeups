# Broken?
Points: 490 (18 Solves)
## Description
You find his laptop lying there and his futile attempt to read a random file..!
## Instance and Attachments
- We can launch our own instance of the chall. Server code [chall.py](Attachments/chall.py) is also provided ![2](Attachments/2.png)
## Solution
- Running `nc kashictf.iitbhucybersec.in 39323`, I get this output:
```
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
```
- First of all, I don't know why this chall isn't included in the crypto category. Anyways, going through the provided [chall.py](Attachments/chall.py) file, I took the help of an LLM to understand what's going on:
  - The server receives data. It uses [HMAC](https://en.wikipedia.org/wiki/HMAC) for validation, comparing a computed signature against a received one. `HMAC` is a hash-based message authentication code and is used to verify the integrity and authenticity of a message. It involves a cryptographic hash function in combination with a secret key.
  - The Python code defines a `generate_hmac` function, and the server waits for a request with a specific format `(data|hmac)`.
  - Standard implementations of `HMAC` are not susceptible to length extension attacks, but the server code is using a custom implementation of `HMAC`. The code computes HMAC manually using `hashlib.sha1(SECRET_KEY + message.encode())`.
- I also noted that the code uses [SHA-1](https://en.wikipedia.org/wiki/SHA-1) for hashing. It's not considered secure anymore due to its vulnerabilities. It's prone to length extension attacks.
- So, if we have `hash = SHA1(secret + original_message)`, we can compute `new_hash = SHA1(secret + original_message + padding + appended_data)` without knowing the secret key.
- I highly recommend reading [this](https://en.wikipedia.org/wiki/Length_extension_attack) Wikipedia article to understand length extension attacks.
- It's safe to assume that the flag is probably located in a file named `flag.txt`. So we need to append `&file=flag.txt` to the original message. From the [length extension wiki](https://en.wikipedia.org/wiki/Length_extension_attack):
```
This can be done by taking advantage of a flexibility in the message format if duplicate content in the query string gives preference to the latter value. This flexibility does not indicate an exploit in the message format, because the message format was never designed to be cryptographically secure in the first place, without the signature algorithm to help it.
```
- This makes our Desired New Data to be: `count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt&file=flag.txt`.
- There's only one small problem, we don't know the length of the key used to generate the HMAC. But I believe that can be easily brute-forced. I learnt of a tool called [HashPump](https://github.com/miekrr/HashPump) that can be used to perform length extension attacks. I ran `git clone https://github.com/miekrr/HashPump` to clone the repository.
- After `cd`ing into the `HashPump` directory, I ran `g++ -o hashpump main.cpp Extender.cpp MD4ex.cpp MD5ex.cpp SHA1.cpp SHA256.cpp SHA512ex.cpp -O2 -std=c++11 -I$(brew --prefix openssl)/include -L$(brew --prefix openssl)/lib -lcrypto` to compile the tool. It basically takes all the source code files and builds them into an executable called `hashpump`, using the `openssl` crypto library to perform the hashing. I got this command from an LLM.
- With the help of the [README](https://github.com/miekrr/HashPump/blob/master/README.md) file, I ran the following command:
```
./hashpump -s 01be4a249bed4886b93d380daba91eb4a0b1ee29 -d "count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt" -a "&file=flag.txt" -k 8
2102c0554554f53e70fd29e4a9dab491fe8ec17b
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x18&file=flag.txt
```
- I guessed the key length to be 8 for now. At least the tool is working fine. The output is the new hash and the new message. We need to send this in the expected format `data|new_hmac` to the server. I ran the following command to send the new data to the server:
```
echo -e "count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x18&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b" | nc kashictf.iitbhucybersec.in 39900
```
- But I got the `Invalid HMAC. Try again.` response. This means that the key length is not 8. Instead of doing this manually, I wrote a [script](./solve.py) with the help of an LLM to brute-force the key length:
```python
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
```
- The script does the following:
  - Loops over a range of guessed key lengths (here from 5 to 50).
  - For each key length, it runs the hashpump tool with the original data, original HMAC, and the appended parameter `(&file=flag.txt)`.
  - The output is split into a new signature and the forged data (which contains the necessary SHA1 padding).
  - It then builds the final payload as `forged_data|new_signature`.
  - Using a socket connection, it sends the payload to the server at `kashictf.iitbhucybersec.in` on port 39900 and prints the response.
  - If the response contains the word “KashiCTF{” (case-insensitive), it stops.
- Running the script, I got the flag:
```
python3 solve.py
Starting bruteforce over key lengths from 5 to 50

[*] Trying key length: 5
[*] Forged payload for key length 5:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 6
[*] Forged payload for key length 6:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x08&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 7
[*] Forged payload for key length 7:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x10&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 8
[*] Forged payload for key length 8:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x18&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 9
[*] Forged payload for key length 9:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02 &file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 10
[*] Forged payload for key length 10:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02(&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 11
[*] Forged payload for key length 11:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x020&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 12
[*] Forged payload for key length 12:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x028&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 13
[*] Forged payload for key length 13:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02@&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 14
[*] Forged payload for key length 14:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02H&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 15
[*] Forged payload for key length 15:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02P&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
Invalid HMAC. Try again.


[*] Trying key length: 16
[*] Forged payload for key length 16:
count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02X&file=flag.txt|2102c0554554f53e70fd29e4a9dab491fe8ec17b
[*] Server response:
Retrieve file using format: data|hmac
Example: count=10&lat=37.351&user_id=1&long=-119.827&file=random.txt|01be4a249bed4886b93d380daba91eb4a0b1ee29
File Contents:
KashiCTF{Close_Yet_Far_wyP0xq7M0}

[+] Flag found!
```
- The flag is `KashiCTF{Close_Yet_Far_wyP0xq7M0}`.