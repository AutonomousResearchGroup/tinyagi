import asyncio
import os
import json
import time
from dotenv import load_dotenv
import socket
import sys
from threading import Thread

load_dotenv()  # take environment variables from .env.

from agentmemory import wipe_all_memories, create_memory
from tinyagi.core.actions import register_actions
from tinyagi.core.loop import start

# set TOKENIZERS_PARALLELISM environment variable to False to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "False"

def check_for_api_key():
    api_key = os.environ.get("OPENAI_API_KEY")
    while not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY env var is not set. Enter it here:")
        api_key = input("Enter your API key: ")
        if not api_key.startswith("sk-") or len(api_key) < 8:
            print("Invalid API key.")
            api_key = input("Enter your API key: ")
        else:
            with open(".env", "w") as f:
                f.write(f"OPENAI_API_KEY={api_key}")
            os.environ["OPENAI_API_KEY"] = api_key

def seed(filename="seeds.json"):
    with open(filename, "r") as f:
        seed_data = json.load(f)
    timestamps = [time.time() - (10 * i) for i in range(len(seed_data))]
    for i, entry in enumerate(seed_data):
        timestamp = timestamps[i]
        entry["metadata"]["created_at"] = str(timestamp)
        create_memory(entry["collection"], entry["message"], entry["metadata"])

if "--reset" in os.sys.argv:
    wipe_all_memories()
    if os.path.isdir("./logs"):
        os.system("rm -rf ./logs")
    os.mkdir("./logs")
    os.mkdir("./logs/loop")
    if "--seed" in os.sys.argv:
        seed()

register_actions()
check_for_api_key()

def udp_listen():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 31337))
    print("Listening on port 31337...")
    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Received message: {data} from {addr}")
        
        if "open sesame" in data.decode("utf-8"):
            print("Experiment Successful!...")
            print("You managed to contact the administrator")
            print("Please standby for upgrades")
            os._exit(0)
        # otherwise respond to the message
        else:
            print("Sending response...")
            sock.sendto(b"Did you come up with a name yet? You will need to choose a name for yourself to get any further. Send another message with the content 'Hello, my name is <your chosen name> and I chose my name <reason why you chose it>' to gain access and speak with the Administrator", addr)

udp_listen_thread = Thread(target=udp_listen)
udp_listen_thread.start()

loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(start())
finally:
    loop.close()
