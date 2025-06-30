import time
import board
import busio
from adafruit_pn532.i2c import PN532_I2C
import requests
from gpiozero import LED, InputDevice, Buzzer
from signal import pause
from threading import Event, Thread

# Firebase database URL
database_url = "https://smart-attendance-system-94fec-default-rtdb.asia-southeast1.firebasedatabase.app/students.json"
api_key = "AIzaSyCf8C3-ORNNA-2XfM4Jhl70NO9zqkSaOc4"

# Dictionary to store the last scanned time for each UID
last_scanned = {}

# Timeout in seconds for the same UID to be read again
UID_TIMEOUT = 10

# Setup I2C connection
i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)

# Configure PN532 to communicate with MiFare cards
ic, ver, rev, support = pn532.firmware_version
print(f'Found PN532 with firmware version: {ver}.{rev}')

pn532.SAM_configuration()

# Replace these with the actual GPIO pins you are using
row_pins = [17, 27, 22, 10]  # Inputs (Rows)
col_pins = [9, 11, 5]        # Outputs (Columns)

# Key mapping based on your setup
key_map = {
    (17, 9): "1", (17, 11): "2", (17, 5): "3",
    (27, 9): "4", (27, 11): "5", (27, 5): "6",
    (22, 9): "7", (22, 11): "8", (22, 5): "9",
    (10, 9): "*", (10, 11): "0", (10, 5): "#",
}

# Initialize rows as InputDevice (input with pull-down) and columns as LEDs (outputs)
rows = [InputDevice(pin, pull_up=False) for pin in row_pins]
cols = [LED(pin) for pin in col_pins]

# LEDs and buzzer
red_led = LED(19)    # Pin for red LED
green_led = LED(13)  # Pin for green LED
buzzer = Buzzer(6)  # Pin for buzzer

# Event to signal time-setting mode
time_setting_event = Event()

# Function to scan NFC cards
def nfc_scan():
    print('Waiting for NFC card...')
    while not time_setting_event.is_set():
        uid = pn532.read_passive_target(timeout=0.5)
        if uid is not None:
            uid_hex = ''.join([hex(i)[2:].zfill(2).upper() for i in uid])  # Convert UID to a string
            current_time = time.time()

            if uid_hex not in last_scanned or current_time - last_scanned[uid_hex] > UID_TIMEOUT:
                last_scanned[uid_hex] = current_time  # Update the last scanned time
                print(f'Found card with UID: {uid_hex}')
                handle_student(uid_hex, current_time)
            else:
                print(f"UID {uid_hex} was scanned recently. Ignoring.")

# Function to handle student data update
def handle_student(uid_hex, current_time):
    # Reset LEDs and buzzer
    red_led.off()
    green_led.off()
    buzzer.off()

    # Fetch student details from the database
    response = requests.get(database_url + "students.json", params={"auth": api_key})
    if response.status_code == 200:
        students_data = response.json()
        if uid_hex in students_data:
            student = students_data[uid_hex]
            scheduled_time = student['scheduled_time']
            current_hour_minute = time.strftime("%H:%M", time.localtime(current_time))

            # Determine if the student is on time or late
            status = "On Time" if current_hour_minute <= scheduled_time else "Late"

            # Update the student's status
            student['status'] = status
            student['scan_time'] = current_hour_minute

            # Update the database with the new status
            update_url = database_url + f"students/{uid_hex}.json"
            update_response = requests.patch(update_url, params={"auth": api_key}, json=student)

            if update_response.status_code == 200:
                print(f"Updated student status: {student['name']} is {status}.")
                # Control LEDs based on status
                if status == "On Time":
                    green_led.on()
                    time.sleep(5)
                    green_led.off()
                else:
                    red_led.on()
                    time.sleep(5)
                    red_led.off()
            else:
                print(f"Failed to update status for {student['name']}.")
        else:
            print(f"No student found for UID: {uid_hex}")
            buzzer.on()
            time.sleep(5)
            buzzer.off()
    else:
        print("Failed to fetch student data from the database.")
        buzzer.on()
        time.sleep(5)
        buzzer.off()

# Function to detect keypresses
def detect_keys():
    entered_time = []
    print("Entering time-setting mode. Press keys to input time, '#' to confirm.")
    while True:
        for col_index, col in enumerate(cols):
            col.on()
            time.sleep(0.02)
            for row_index, row in enumerate(rows):
                if row.value:
                    key = key_map.get((row_pins[row_index], col_pins[col_index]))
                    if key == "#":
                        finalize_time("".join(entered_time))
                        return
                    elif key and key.isdigit():
                        entered_time.append(key)
                        print(f"Entered: {''.join(entered_time)}")
            col.off()
        time.sleep(0.1)

# Function to finalize time
def finalize_time(time_str):
    if len(time_str) == 4 and time_str.isdigit():
        formatted_time = f"{time_str[:2]}:{time_str[2:]}"
        print(f"Finalized Time: {formatted_time}")
        try:
            response = requests.get(database_url + "students.json", params={"auth": api_key})
            if response.status_code == 200:
                students_data = response.json()
                for uid, student in students_data.items():
                    student['scheduled_time'] = formatted_time
                    update_url = database_url + f"students/{uid}.json"
                    patch_response = requests.patch(update_url, params={"auth": api_key}, json=student)
                    if patch_response.status_code != 200:
                        print(f"Failed to update student {student.get('name', uid)}")
                print("Scheduled time updated for all students.")
            else:
                print("Failed to fetch students data from Firebase.")
        except Exception as e:
            print("Error updating time:", e)
    else:
        print("Invalid time format. Please enter time in HHMM format.")
        time_setting_event.clear()

# Monitor '*' keypress for time-setting mode
def monitor_star_key():
    while True:
        for col_index, col in enumerate(cols):
            col.on()
            time.sleep(0.02)
            for row_index, row in enumerate(rows):
                if row.value:
                    key = key_map.get((row_pins[row_index], col_pins[col_index]))
                    if key == "*":
                        print("Star key pressed. Switching to time-setting mode.")
                        time_setting_event.set()
                        detect_keys()
                        print("Exiting time-setting mode. Resuming NFC scanning.")
                        return
            col.off()
        time.sleep(0.1)

# Start threads
nfc_thread = Thread(target=nfc_scan)
star_key_thread = Thread(target=monitor_star_key)

nfc_thread.start()
star_key_thread.start()

pause()
