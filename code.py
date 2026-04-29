import RPi.GPIO as GPIO
import time

MOTOR_PINS = {
    'AIN1': 18,
    'AIN2': 17,
    'BIN1': 22,
    'BIN2': 27,
    'PWM_A': 13,
    'PWM_B': 19,
}

# ── 3 IR Sensors (LEFT, CENTER, RIGHT) ──
SENSOR_PINS = [23, 25, 24]

BASE_SPEED = 60
TURN_SPEED = 80
MAX_SPEED = 100
MIN_SPEED = 0

GPIO.setmode(GPIO.BCM)

for pin in MOTOR_PINS.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

pwm_a = GPIO.PWM(MOTOR_PINS['PWM_A'], 1000)
pwm_b = GPIO.PWM(MOTOR_PINS['PWM_B'], 1000)
pwm_a.start(0)
pwm_b.start(0)

for pin in SENSOR_PINS:
    GPIO.setup(pin, GPIO.IN)


def set_motor_speed(speed_a, speed_b):
    # Left motor
    if speed_a >= 0:
        GPIO.output(MOTOR_PINS['AIN1'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['AIN2'], GPIO.LOW)
        pwm_a.ChangeDutyCycle(min(abs(speed_a), 100))
    else:
        GPIO.output(MOTOR_PINS['AIN1'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['AIN2'], GPIO.HIGH)
        pwm_a.ChangeDutyCycle(min(abs(speed_a), 100))

    # Right motor
    if speed_b >= 0:
        GPIO.output(MOTOR_PINS['BIN1'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['BIN2'], GPIO.LOW)
        pwm_b.ChangeDutyCycle(min(abs(speed_b), 100))
    else:
        GPIO.output(MOTOR_PINS['BIN1'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['BIN2'], GPIO.HIGH)
        pwm_b.ChangeDutyCycle(min(abs(speed_b), 100))


def stop_motors():
    set_motor_speed(0, 0)


def read_sensors():
    return [GPIO.input(pin) for pin in SENSOR_PINS]


# 🔥 NEW LOGIC FOR 3 SENSORS
last_error = 0

def line_follower_logic():
    global last_error

    sensors = read_sensors()
    L, C, R = sensors

    # ── Determine error ──
    if sensors == [0, 1, 0]:
        error = 0  # centered
    elif sensors in ([1, 0, 0], [1, 1, 0]):
        error = -1  # left
    elif sensors in ([0, 0, 1], [0, 1, 1]):
        error = 1   # right
    elif sensors == [1, 1, 1]:
        print("End of line detected")
        stop_motors()
        return 0, 0
    else:
        # line lost → use last direction
        error = last_error

    last_error = error

    # ── Motor control ──
    if error == 0:
        left_speed = BASE_SPEED
        right_speed = BASE_SPEED

    elif error == -1:  # turn left
        left_speed = 0
        right_speed = TURN_SPEED

    elif error == 1:  # turn right
        left_speed = TURN_SPEED
        right_speed = 0

    # Clamp
    left_speed = max(MIN_SPEED, min(MAX_SPEED, left_speed))
    right_speed = max(MIN_SPEED, min(MAX_SPEED, right_speed))

    print(f"Sensors: {sensors} -> L={left_speed} R={right_speed}", end='\r')

    return left_speed, right_speed


def main():
    print("\n--- 3 Sensor Line Follower ---")

    try:
        while True:
            left_speed, right_speed = line_follower_logic()
            set_motor_speed(left_speed, right_speed)
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stop_motors()
        pwm_a.stop()
        pwm_b.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
