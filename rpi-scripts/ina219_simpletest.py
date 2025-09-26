# ina_monitor.py

import time
import board
from adafruit_ina219 import INA219

def start_power_monitoring(stop_event, log_path="power_log.txt"):
    i2c_bus = board.I2C()
    ina219 = INA219(i2c_bus)

    ina219.set_calibration_16V_2_5A()

    last_power = None
    start_time = time.time()

    with open(log_path, "w") as log_file:
        log_file.write("=== INA219 Power Monitoring Log ===\n\n")
        log_file.write("Config register:\n")
        log_file.write("  bus_voltage_range:    0x%1X\n" % ina219.bus_voltage_range)
        log_file.write("  gain:                 0x%1X\n" % ina219.gain)
        log_file.write("  bus_adc_resolution:   0x%1X\n" % ina219.bus_adc_resolution)
        log_file.write("  shunt_adc_resolution: 0x%1X\n" % ina219.shunt_adc_resolution)
        log_file.write("  mode:                 0x%1X\n\n" % ina219.mode)

        print("Started INA219 power monitoring...")

        while not stop_event.is_set():
            power = ina219.power
            current_time = time.time()

            if last_power is None:
                last_power = power
                start_time = current_time
            elif power != last_power:
                duration = current_time - start_time
                msg1 = f"Power changed from {last_power:6.3f} W after {duration:6.3f} seconds\n"
                msg2 = f"Power Register : {power:6.3f}   W\n\n"
                log_file.write(msg1)
                log_file.write(msg2)
                print(msg1 + msg2, end="")
                last_power = power
                start_time = current_time
            else:
                msg = f"Power Register : {power:6.3f}   W\n\n"
                log_file.write(msg)
                print(msg, end="")

            if ina219.overflow:
                overflow_msg = "Internal Math Overflow Detected!\n\n"
                log_file.write(overflow_msg)
                print(overflow_msg, end="")

            #time.sleep(1)  # adjust interval as needed

        print("Stopped INA219 power monitoring.")

if __name__ == "__main__":
    import threading

    stop_event = threading.Event()
    try:
       start_power_monitoring(stop_event, "alex_metrics_v6.txt")
    except KeybordInterrupt:
       stop_event.set()
       print("\nStopped by user")
