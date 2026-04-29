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

# ── 3 IR Sensors (Left, Center, Right) ──────────────────────────────────────
SENSOR_PINS = [23, 25, 24]   # [LEFT, CENTER, RIGHT] — edit GPIO numbers as needed

# ── Speed Parameters ─────────────────────────────────────────────────────────
BASE_SPEED = 60     # Straight-line speed (0–100)
MAX_SPEED  = 80     # Hard cap on any motor
MIN_SPEED  = 0

# ── PID Tuning Knobs ──────────────────────────────────────────────────────────
# Start with Kp only, then add Kd for damping overshoot, Ki usually stays ~0
KP = 25.0   # Proportional gain  — bigger = more aggressive steering
KD = 10.0   # Derivative gain    — dampens oscillation / overshoot on curves
KI =  0.0   # Integral gain      — corrects steady-state drift (usually 0)

# ─────────────────────────────────────────────────────────────────────────────

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


# ── PID State ─────────────────────────────────────────────────────────────────
last_error   = 0
integral     = 0
last_time    = time.time()


def set_motor_speed(speed_a, speed_b):
    """Drive motors. Positive = forward, negative = backward."""
    # Left motor (A)
    if speed_a >= 0:
        GPIO.output(MOTOR_PINS['AIN1'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['AIN2'], GPIO.LOW)
        pwm_a.ChangeDutyCycle(min(speed_a, 100))
    else:
        GPIO.output(MOTOR_PINS['AIN1'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['AIN2'], GPIO.HIGH)
        pwm_a.ChangeDutyCycle(min(-speed_a, 100))

    # Right motor (B)
    if speed_b >= 0:
        GPIO.output(MOTOR_PINS['BIN1'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['BIN2'], GPIO.LOW)
        pwm_b.ChangeDutyCycle(min(speed_b, 100))
    else:
        GPIO.output(MOTOR_PINS['BIN1'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['BIN2'], GPIO.HIGH)
        pwm_b.ChangeDutyCycle(min(-speed_b, 100))


def stop_motors():
    set_motor_speed(0, 0)


def read_sensors():
    """Returns [LEFT, CENTER, RIGHT] as 0/1 values."""
    return [GPIO.input(pin) for pin in SENSOR_PINS]


def get_error(sensors):
    """
    Map 3-sensor readings to a positional error.
      -1 = line is LEFT   (turn left)
       0 = line is CENTER (go straight)
      +1 = line is RIGHT  (turn right)
    Returns None if all sensors are off (lost line).
    """
    L, C, R = sensors

    if   sensors == [0, 1, 0]: return  0   # Centered
    elif sensors == [1, 0, 0]: return -1   # Line left
    elif sensors == [0, 0, 1]: return  1   # Line right
    elif sensors == [1, 1, 0]: return -1   # Leaning left
    elif sensors == [0, 1, 1]: return  1   # Leaning right
    elif sensors == [1, 1, 1]: return  None  # End of line / junction
    elif sensors == [1, 0, 1]: return  0   # Straddle (treat as center)
    else:                       return  None  # All off — line lost


def pid_control(error):
    """
    Computes a correction value using PID.
    Positive correction = steer right, negative = steer left.
    """
    global last_error, integral, last_time

    now = time.time()
    dt  = now - last_time
    if dt <= 0:
        dt = 0.02

    integral  += error * dt
    derivative = (error - last_error) / dt

    correction = (KP * error) + (KI * integral) + (KD * derivative)

    last_error = error
    last_time  = now

    return correction


def line_follower_step():
    """Single control loop iteration. Returns False if robot should stop."""
    global last_error

    sensors = read_sensors()
    error   = get_error(sensors)

    # ── End-of-line / junction ────────────────────────────────────────────────
    if sensors == [1, 1, 1]:
        print("[LINE] All sensors on — end of line / junction detected. Stopping.")
        stop_motors()
        return False

    # ── Line lost — use last known error to keep turning ─────────────────────
    if error is None:
        print(f"[LINE] Lost line — coasting on last error ({last_error})")
        error = last_error   # Hold last direction

    correction = pid_control(error)

    left_speed  = BASE_SPEED - correction   # Reduce left  when turning right
    right_speed = BASE_SPEED + correction   # Reduce right when turning left

    # Clamp to valid PWM range
    left_speed  = max(MIN_SPEED, min(MAX_SPEED, left_speed))
    right_speed = max(MIN_SPEED, min(MAX_SPEED, right_speed))

    print(f"[PID] S={sensors} err={error:+.1f} cor={correction:+.1f} "
          f"L={left_speed:.0f} R={right_speed:.0f}", end='\r')

    set_motor_speed(left_speed, right_speed)
    return True


# ── Test Helpers ──────────────────────────────────────────────────────────────

def test_motors():
    print("\n--- Motor Test ---")
    input("Enter → FORWARD "); set_motor_speed(BASE_SPEED, BASE_SPEED); time.sleep(2)
    input("Enter → BACKWARD"); set_motor_speed(-BASE_SPEED, -BASE_SPEED); time.sleep(2)
    input("Enter → LEFT    "); set_motor_speed(-30, 30); time.sleep(2)
    input("Enter → RIGHT   "); set_motor_speed(30, -30); time.sleep(2)
    input("Enter → STOP    "); stop_motors()
    print("--- Motor Test Done ---\n")


def test_sensors():
    print("\n--- Sensor Test (Ctrl+C to exit) ---")
    print("Pins: LEFT={} CENTER={} RIGHT={}".format(*SENSOR_PINS))
    try:
        while True:
            s = read_sensors()
            bar = ['L' if s[0] else '-', 'C' if s[1] else '-', 'R' if s[2] else '-']
            print(f"  Raw: {s}  Visual: {''.join(bar)}", end='\r')
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n--- Sensor Test Done ---\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*50)
    print("  Raspberry Pi Line Follower — 3 Sensor + PID")
    print("="*50)

    if input("\nRun motor test? (y/n): ").lower() == 'y':
        test_motors()

    if input("Run sensor test? (y/n): ").lower() == 'y':
        test_sensors()

    print("\n--- Starting Line Following ---")
    print("Place robot on the line. Press Ctrl+C to stop.\n")

    try:
        while True:
            if not line_follower_step():
                break
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\n\n--- Stopping ---")
    finally:
        stop_motors()
        pwm_a.stop()
        pwm_b.stop()
        GPIO.cleanup()
        print("GPIO cleaned up. Goodbye!")


if __name__ == "__main__":
    main()
