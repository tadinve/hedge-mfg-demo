# Import necessary libraries
import requests
import json
import time
import re
import serial
import argparse
import random
# Define API endpoint and connection details
API_URL = 'https://vmyreqq3bh.execute-api.us-east-1.amazonaws.com/devices'
AUTH_CREDENTIALS = ('mailto:troy_cline@bmc.com', 'helixdemo2022')
HEADERS = {'Content-Type': 'application/json'}
PORT = "COM5"  # Serial port to connect to
MAX_ITERATIONS = 3600  # Default number of times, main function will run (roughly equivalent to seconds)
BAUD_RATE = 115200  # Baud rate for serial communication
DEFAULT_DEVICE_ID = "17"  # Default device ID to use if none provided


# Get the arguments from cmd line
def get_arguments():
    parser = argparse.ArgumentParser(description="Input Arguments")
    parser.add_argument('-i', '--iterations', type=int, default=800, help="Max number of times code will run.")
    args = parser.parse_args()
    return args

# Extract numerical values from the given log line
def extract_numbers(log_line):
    match = re.search(r'Angle\(ABCDXYZ\):([^|]+)', log_line)
    if not match:
        return []
    numbers = [float(value.strip()) for value in match.group(1).split(',')[:6]]
    return numbers

# Send the given payload to the defined API endpoint
def post_json_to_api(payload):
    print('Payload:', payload)
    response = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload), auth=AUTH_CREDENTIALS)
    print('Response:', response.status_code)
    print('Response content:', response.content)
    print('---')

# Process a log line, extract numbers, and post the result to API
def process_log_line(log_line, device_id, prev_position, idle_count):
    numbers = extract_numbers(log_line)
    
    # Formulate payload for the device's current position
    payload = {
        "deviceId": device_id,
        "baseRotation": numbers[0],
        "lowerArm": numbers[1],
        "upperArm": numbers[2],
        "wristRotation": random.randint(-1800,1800)/10,
        "wristAngle": numbers[4],
        "endAngle": numbers[5],
    }
    
    # Check if device position hasn't changed
    if numbers == prev_position:
        idle_count += 1
    else:
        idle_count = 0
        prev_position = numbers
    
    # If device has been idle for two or more cycles, send an error payload
    if idle_count >= 4:
        payload = {
            "deviceId": device_id,
            "errortitle": "Arm Idle/Waiting",
            "errorMessage": "Process Inoperational Check Packaging Station",
        }
    
    post_json_to_api(payload)
    return prev_position, idle_count

# Main function to handle serial communication and process device data.
def main(MAX_ITERATIONS):
    
    # Attempt to establish a serial connection
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
    except serial.SerialException as e:
        print(f"Error establishing serial connection: {e}")
        return

    prev_position = [0, 0, 0]
    idle_count = 0

    # Read and process data from the device for the defined number of iterations
    for _ in range(MAX_ITERATIONS):
        
        # Attempt to write a command to the device
        try:
            ser.write("?".encode())
        except serial.SerialException as e:
            print(f"Error writing to device: {e}")
            continue   
        
        time.sleep(1.5)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # Attempt to read the response from the device
        try:
            read_val = ser.read(size=512)
        except serial.SerialException as e:
            print(f"Error reading from device: {e}")
            continue
        
        # Check if any data was received from the device
        if not read_val:
            print("Device did not respond or returned unexpected data.")
            continue
        
        rec = f"{current_time}|{read_val.decode()}\n"

        # Process the received data
        try:
            prev_position, idle_count = process_log_line(rec, DEFAULT_DEVICE_ID, prev_position, idle_count)
        except Exception as e:
            print(f"Ignoring record due to error: {e}")

        print(rec)

    # Close the serial connection when done
    try:
        ser.close()
    except serial.SerialException as e:
        print(f"Error closing the serial connection: {e}")

# Execute the main function when script is run
if __name__ == "__main__":
    args = get_arguments()
    main(args.iterations)
