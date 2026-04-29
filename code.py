import RPi.GPIO as GPIO
import time

MOTOR_PINS = {
    'AIN1': 22,   # Input 1 for Motor A (Left Motor)
    'AIN2': 27,   # Input 2 for Motor A (Left Motor)
    'BIN1': 13,   # Input 1 for Motor B (Right Motor)
    'BIN2': 19,   # Input 2 for Motor B (Right Motor)
    'PWM_A': 23,  # PWM Enable pin for Motor A
    'PWM_B': 24,  # PWM Enable pin for Motor B
}

# GPIO pins for the 5 IR sensors (order: leftmost to rightmost)
SENSOR_PINS = [2, 3, 4, 17, 27]  # GPIO2, GPIO3, GPIO4, GPIO17, GPIO27

# Motor speed and turning parameters (adjust as needed)
BASE_SPEED = 50      # Base speed percentage (0-100)
TURN_SPEED = 40      # Speed for turning (lower = smoother turns)
MAX_SPEED = 80       # Maximum motor speed
MIN_SPEED = 0        # Minimum motor speed

SENSOR_THRESHOLD = 500

GPIO.setmode(GPIO.BCM)  # Use Broadcom pin numbering

for pin in MOTOR_PINS.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# Setup PWM on the enable pins
pwm_a = GPIO.PWM(MOTOR_PINS['PWM_A'], 1000)  # 1kHz frequency
pwm_b = GPIO.PWM(MOTOR_PINS['PWM_B'], 1000)
pwm_a.start(0)
pwm_b.start(0)

# Setup sensor pins as inputs
for pin in SENSOR_PINS:
    GPIO.setup(pin, GPIO.IN)

def set_motor_speed(speed_a, speed_b):
    # Left motor (Motor A)
    if speed_a >= 0:
        GPIO.output(MOTOR_PINS['AIN1'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['AIN2'], GPIO.LOW)
        pwm_a.ChangeDutyCycle(speed_a)
    else:
        GPIO.output(MOTOR_PINS['AIN1'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['AIN2'], GPIO.HIGH)
        pwm_a.ChangeDutyCycle(-speed_a)

    # Right motor (Motor B)
    if speed_b >= 0:
        GPIO.output(MOTOR_PINS['BIN1'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['BIN2'], GPIO.LOW)
        pwm_b.ChangeDutyCycle(speed_b)
    else:
        GPIO.output(MOTOR_PINS['BIN1'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['BIN2'], GPIO.HIGH)
        pwm_b.ChangeDutyCycle(-speed_b)

def stop_motors():
    """Stops both motors."""
    set_motor_speed(0, 0)

def read_sensors():
    sensor_values = []
    for pin in SENSOR_PINS:
        value = GPIO.input(pin)
        sensor_values.append(value)
    return sensor_values

def test_motors():
    print("\n--- Motor Test Starting ---")
    input("Press Enter to move FORWARD...")
    set_motor_speed(BASE_SPEED, BASE_SPEED)
    time.sleep(2)

    input("Press Enter to move BACKWARD...")
    set_motor_speed(-BASE_SPEED, -BASE_SPEED)
    time.sleep(2)

    input("Press Enter to turn LEFT...")
    set_motor_speed(-TURN_SPEED, TURN_SPEED)
    time.sleep(2)

    input("Press Enter to turn RIGHT...")
    set_motor_speed(TURN_SPEED, -TURN_SPEED)
    time.sleep(2)

    input("Press Enter to STOP...")
    stop_motors()
    print("--- Motor Test Complete ---\n")

def test_sensors():
    print("\n--- Sensor Test ---")
    print("Place the robot on line and surface to see sensor values.")
    print("Press Ctrl+C to exit test.\n")
    try:
        while True:
            sensors = read_sensors()
            visual = ''.join(['X' if s else '-' for s in sensors])
            print(f"Sensors: {sensors} -> {visual}", end='\r')
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n--- Sensor Test Complete ---\n")

def line_follower_logic():

    sensors = read_sensors()
    error = 0
    
    if sensors == [1, 0, 0, 0, 0]:
        error = -2  # Line is far left
    elif sensors == [0, 1, 0, 0, 0]:
        error = -1  # Line is slightly left
    elif sensors == [0, 0, 1, 0, 0]:
        error = 0   # Line is centered
    elif sensors == [0, 0, 0, 1, 0]:
        error = 1   # Line is slightly right
    elif sensors == [0, 0, 0, 0, 1]:
        error = 2   # Line is far right
    elif sensors == [1, 1, 0, 0, 0]:
        error = -2  # Line is left (on junction/curve)
    elif sensors == [0, 0, 0, 1, 1]:
        error = 2   # Line is right (on junction/curve)
    elif sensors == [1, 1, 1, 0, 0]:
        error = -2
    elif sensors == [0, 0, 1, 1, 1]:
        error = 2
    elif sensors == [1, 1, 1, 1, 1]:
        print("--- End of line detected! ---")
        stop_motors()
        return 0, 0
    else:
        # Default fallback (should not happen with clean line)
        error = 0
    
    # Calculate motor speeds based on error
    if error == 0:
        # Move straight
        left_speed = BASE_SPEED
        right_speed = BASE_SPEED
    elif error == -2:  # Sharp left turn
        left_speed = -TURN_SPEED   # Left motor reverse
        right_speed = TURN_SPEED   # Right motor forward
    elif error == -1:  # Soft left turn
        left_speed = 0             # Left motor stop
        right_speed = BASE_SPEED   # Right motor forward
    elif error == 1:   # Soft right turn
        left_speed = BASE_SPEED    # Left motor forward
        right_speed = 0            # Right motor stop
    elif error == 2:   # Sharp right turn
        left_speed = TURN_SPEED    # Left motor forward
        right_speed = -TURN_SPEED  # Right motor reverse
    else:
        left_speed = BASE_SPEED
        right_speed = BASE_SPEED
    
    # Apply speed limits
    left_speed = max(MIN_SPEED, min(MAX_SPEED, left_speed))
    right_speed = max(MIN_SPEED, min(MAX_SPEED, right_speed))
    
    return left_speed, right_speed

def main():
    print("\n" + "="*50)
    print("  Raspberry Pi Line Follower Robot")
    print("="*50)
    
    # Optional: Motor test
    response = input("\nRun motor test? (y/n): ").lower()
    if response == 'y':
        test_motors()
    
    # Optional: Sensor test
    response = input("Run sensor test? (y/n): ").lower()
    if response == 'y':
        test_sensors()
    
    print("\n--- Starting Line Following ---")
    print("Place robot on the line track.")
    print("Press Ctrl+C to stop.\n")
    
    try:
        while True:
            left_speed, right_speed = line_follower_logic()
            set_motor_speed(left_speed, right_speed)
            time.sleep(0.02)  # Small delay for stability
            
    except KeyboardInterrupt:
        print("\n\n--- Stopping robot ---")
        stop_motors()
        pwm_a.stop()
        pwm_b.stop()
        GPIO.cleanup()
        print("GPIO cleaned up. Goodbye!")

if __name__ == "__main__":
    main()
