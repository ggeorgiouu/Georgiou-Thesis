import threading
from inference_yolo import run_inference
from ina219_simpletest import start_power_monitoring

def main():
    stop_event = threading.Event()

    # Start INA monitor in a separate thread
    ina_thread = threading.Thread(
        target=start_power_monitoring,
        args=(stop_event, "test.txt"),
        daemon=True
    )
    ina_thread.start()

    # Run inference in the main thread
    run_inference()

    # Signal INA to stop after inference is done
    stop_event.set()
    ina_thread.join()

    print("\nAll done. Power log saved to 'power_log.txt'.")

if __name__ == "__main__":
    main()
