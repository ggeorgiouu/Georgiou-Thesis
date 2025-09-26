import os
import queue
import zenoh
import time

WORKDIR = "/home/ggeorgiou/storage/pv-hawk-tutorial/workdir"
FOLDERS_TO_SEND = ["splitted", "quadrilaterals", "tracking"]
#FOLDERS_TO_SEND = ["quadrilaterals", "tracking"]

acks = queue.Queue()

def ack_listener(sample):
    ack_key = str(sample.key_expr)
    print(f"[Publisher] Received ACK for {ack_key}")
    acks.put(ack_key)

def split_file(filepath, chunk_size=128*1024):  
    with open(filepath, 'rb') as f:
        chunk_id = 0
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk_id, chunk
            chunk_id += 1

def publish_folder(session, folder_path, key_prefix):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, WORKDIR).replace(os.sep, '/')

            if relative_path.startswith("splitted/"):
                # Send entire file raw, no chunking
                zenoh_key = f"{key_prefix}/{relative_path}"
                with open(file_path, "rb") as f_in:
                    content = f_in.read()
                print(f"[Publisher] Sending raw file {file_path} -> {zenoh_key} (size: {len(content)})")
                session.put(zenoh_key, content)

                expected_ack = f"ack/{zenoh_key}"
                print(f"[Publisher] Waiting for ACK of {expected_ack}...")
                while True:
                    ack_received = acks.get()
                    if ack_received == expected_ack:
                        print(f"[Publisher] ACK confirmed for {zenoh_key}")
                        break

            elif relative_path in ["quadrilaterals/quadrilaterals.pkl", "tracking/tracks.csv"]:
                # Send these specific files chunked as before
                print(f"[Publisher] Sending chunked file {relative_path} -> {file_path}")
                for chunk_id, chunk in split_file(file_path):
                    zenoh_key = f"{key_prefix}/{relative_path}.chunk{chunk_id}"
                    print(f"[Publisher] Sending chunk {chunk_id} -> {zenoh_key} (size: {len(chunk)})")
                    session.put(zenoh_key, chunk)

                    expected_ack = f"ack/{zenoh_key}"
                    print(f"[Publisher] Waiting for ACK of {expected_ack}...")
                    while True:
                        ack_received = acks.get()
                        if ack_received == expected_ack:
                            print(f"[Publisher] ACK confirmed for {zenoh_key}")
                            break

                # Send end-of-file marker after all chunks sent
                end_key = f"{key_prefix}/{relative_path}.end"
                session.put(end_key, b"EOF")
                print(f"[Publisher] Sent end signal for {relative_path}")

                expected_ack = f"ack/{end_key}"
                print(f"[Publisher] Waiting for ACK of {expected_ack}...")
                while True:
                    ack_received = acks.get()
                    if ack_received == expected_ack:
                        print(f"[Publisher] ACK confirmed for {end_key}")
                        break

            else:
                # Ignore other files if any
                continue



def main():
    start_time = time.time()
    conf = zenoh.Config()
    # conf.insert_json5("connect/endpoints", '["tcp:<SERVER_IP>:7447"]')

    print("[Publisher] Connecting to Zenoh...")
    session = zenoh.open(conf)

    # Start subscriber to acks
    session.declare_subscriber("ack/**", ack_listener)

    try:
        for folder in FOLDERS_TO_SEND:
            folder_path = os.path.join(WORKDIR, folder)
            if os.path.exists(folder_path):
                publish_folder(session, folder_path, "workdir")
            else:
                print(f"[Warning] Folder not found: {folder_path}")

        print("[Publisher] Selected folders sent and ACKed!")
        session.put("workdir/done", b"ALL_FILES_SENT")
        print("[Publisher] Completion signal sent.")
    finally:
        session.close()
        end_time = time.time()  # <-- record end time
        elapsed_time = end_time - start_time
        print(f"[Publisher] Script finished in {elapsed_time:.2f} seconds.")

if __name__ == "__main__":
    main()