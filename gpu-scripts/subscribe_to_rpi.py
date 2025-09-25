import os
import subprocess
import zenoh
import subprocess
import threading

DEST_BASE = "/home/ggeo/storage/pv-hawk-tutorial/new_workdir"

def save_file(base_dir, relative_path, data):
    dest_path = os.path.join(base_dir, relative_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(data)
    print(f"[Subscriber] Saved file to {dest_path}")


chunks_store = {}
store_lock = threading.Lock()

def listener_factory(session):
    def listener(sample):
        key = str(sample.key_expr)

        if key == "workdir/done":
            print("[Subscriber] Completion signal received! Starting processing script...")
            subprocess.Popen(["bash", "/home/ggeo/thesis/PV-Hawk/run_app.sh"])
            return

        relative_path = key[len("workdir/"):]
        payload = bytes(sample.payload)

        if relative_path.startswith("splitted/"):
            # Raw file, save immediately
            save_file(DEST_BASE, relative_path, payload)

        elif relative_path.endswith(".end"):
            original_file = relative_path[:-4]  # remove '.end'
            print(f"[Subscriber] Received end signal for {original_file}")

            with store_lock:
                if original_file in chunks_store:
                    chunk_dict = chunks_store[original_file]
                    ordered_chunks = [chunk_dict[i] for i in sorted(chunk_dict.keys())]
                    full_data = b"".join(ordered_chunks)
                    save_file(DEST_BASE, original_file, full_data)
                    del chunks_store[original_file]
                else:
                    print(f"[Subscriber] No chunks found for {original_file} on end signal")

        elif ".chunk" in relative_path:
            base_file, chunk_part = relative_path.rsplit(".chunk", 1)
            chunk_id = int(chunk_part)
            with store_lock:
                if base_file not in chunks_store:
                    chunks_store[base_file] = {}
                chunks_store[base_file][chunk_id] = payload
            print(f"[Subscriber] Stored chunk {chunk_id} of {base_file}")

        else:
            # If any other file (shouldn't happen in your case), just save raw
            save_file(DEST_BASE, relative_path, payload)

        # Send ACK
        ack_key = f"ack/{key}"
        session.put(ack_key, b"ACK")
        print(f"[Subscriber] Sent ACK for {ack_key}")

    return listener



def main():
    conf = zenoh.Config()
    # conf.insert_json5("connect/endpoints", '["tcp:<RPI_IP>:7447"]')

    print("[Subscriber] Connecting to Zenoh...")
    session = zenoh.open(conf)

    try:
        print("[Subscriber] Subscribing to workdir/**")
        session.declare_subscriber("workdir/**", listener_factory(session))
        print("[Subscriber] Ready to receive files. Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Subscriber] Stopping...")
    finally:
        session.close()

if __name__ == "__main__":
    main()
