import RPi.GPIO as GPIO
import time
import pygame
import sys

# -----------------------------
# GPIO PINS
# -----------------------------
TX_PINS = [17, 18, 27, 22, 23, 24, 25, 5]
RX_PINS = [6, 12, 13, 16, 19, 20, 21, 26]

BUTTON_PIN = 7  # Start test button
SWITCH_PIN = 8  # Mode switch

CROSS_MAP = {
    0: 2,
    1: 5,
    2: 0,
    3: 3,
    4: 4,
    5: 1,
    6: 6,
    7: 7
}

# -----------------------------
# GPIO SETUP
# -----------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

def setup_gpio():
    # TX pins idle HIGH
    for pin in TX_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)

    # RX pins with PULL-UP
    for pin in RX_PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Buttons
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def cleanup():
    GPIO.cleanup()

# -----------------------------
# CABLE SCAN FUNCTION
# -----------------------------
def scan_connections(delay=0.01):
    """
    Returns mapping:
    { tx_index: [rx_index, ...] }
    """
    mapping = {}

    # Ensure idle
    for pin in TX_PINS:
        GPIO.output(pin, GPIO.HIGH)

    for tx_index, tx_pin in enumerate(TX_PINS):
        GPIO.output(tx_pin, GPIO.LOW)  # drive active
        time.sleep(delay)

        connected = []
        for rx_index, rx_pin in enumerate(RX_PINS):
            if GPIO.input(rx_pin) == GPIO.LOW:  # active connection
                connected.append(rx_index)

        mapping[tx_index] = connected
        GPIO.output(tx_pin, GPIO.HIGH)  # reset to idle

    return mapping

# -----------------------------
# PYGAME UI SETUP
# -----------------------------
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()

FONT = pygame.font.SysFont("arial", 24)
FONT_SMALL = pygame.font.SysFont("arial", 20)
BIG = pygame.font.SysFont("arial", 56, bold=True)
TITLE_FONT = pygame.font.SysFont("arial", 36, bold=True)

WHITE = (255, 255, 255)
BLACK = (30, 30, 30)
DARK_GRAY = (60, 60, 60)
LIGHT_GRAY = (220, 220, 220)
BLUE = (41, 128, 185)
GREEN = (39, 174, 96)
RED = (231, 76, 60)
ORANGE = (243, 156, 18)
ACCENT = (52, 152, 219)

LEFT_X = 250
RIGHT_X = WIDTH - 250
TOP_Y = 200
SPACING = 50

# -----------------------------
# DRAWING HELPERS
# -----------------------------
def draw_rounded_rect(surface, color, rect, radius=15):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_button(x, y, width, height, text, color, hover=False):
    button_rect = pygame.Rect(x, y, width, height)
    shadow_rect = pygame.Rect(x + 3, y + 3, width, height)
    draw_rounded_rect(screen, DARK_GRAY, shadow_rect, 12)
    btn_color = tuple(min(c + 20, 255) for c in color) if hover else color
    draw_rounded_rect(screen, btn_color, button_rect, 12)
    txt = FONT.render(text, True, WHITE)
    txt_rect = txt.get_rect(center=button_rect.center)
    screen.blit(txt, txt_rect)
    return button_rect

def draw_status_badge(x, y, text, color):
    padding = 20
    txt = FONT_SMALL.render(text, True, WHITE)
    badge_width = txt.get_width() + padding * 2
    badge_height = 35
    badge_rect = pygame.Rect(x, y, badge_width, badge_height)
    draw_rounded_rect(screen, color, badge_rect, 17)
    txt_rect = txt.get_rect(center=badge_rect.center)
    screen.blit(txt, txt_rect)
    return badge_width

def draw_pins(x, label):
    label_txt = TITLE_FONT.render(label, True, BLACK)
    label_rect = label_txt.get_rect(center=(x, TOP_Y - 80))
    screen.blit(label_txt, label_rect)

    positions = []
    for i in range(8):
        y = TOP_Y + i * SPACING
        pygame.draw.circle(screen, DARK_GRAY, (x + 2, y + 2), 18)  # shadow
        pygame.draw.circle(screen, ACCENT, (x, y), 18)
        pygame.draw.circle(screen, WHITE, (x, y), 15)
        pygame.draw.circle(screen, ACCENT, (x, y), 8)
        num_txt = FONT.render(str(i + 1), True, BLACK)
        num_bg_rect = pygame.Rect(x - 60, y - 15, 40, 30)
        draw_rounded_rect(screen, LIGHT_GRAY, num_bg_rect, 8)
        screen.blit(num_txt, (x - 50, y - 12))
        positions.append((x, y))
    return positions

def draw_connections(left_pos, right_pos, mapping, mode):
    for tx, rxs in mapping.items():
        for rx in rxs:
            if mode == "STRAIGHT":
                color = GREEN if len(rxs) == 1 and rx == tx else RED
            else:
                expected_rx = CROSS_MAP.get(tx)
                color = GREEN if len(rxs) == 1 and rx == expected_rx else RED
            width = 5
            pygame.draw.line(screen, (*color[:3], 100), left_pos[tx], right_pos[rx], width + 4)
            pygame.draw.line(screen, color, left_pos[tx], right_pos[rx], width)

def draw_result_panel(status):
    panel_width = 600
    panel_height = 150
    panel_x = 30
    panel_y = HEIGHT - panel_height - 30
    shadow_rect = pygame.Rect(panel_x + 5, panel_y + 5, panel_width, panel_height)
    draw_rounded_rect(screen, DARK_GRAY, shadow_rect, 20)
    color = GREEN if status == "PASS" else RED if status == "FAIL" else LIGHT_GRAY
    panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
    draw_rounded_rect(screen, color, panel_rect, 20)

    if status == "PASS":
        check_center = (panel_x + 80, panel_y + panel_height // 2)
        pygame.draw.circle(screen, WHITE, check_center, 45, 6)
        points = [
            (check_center[0] - 15, check_center[1]),
            (check_center[0] - 5, check_center[1] + 15),
            (check_center[0] + 20, check_center[1] - 15)
        ]
        pygame.draw.lines(screen, WHITE, False, points, 8)
        result_txt = BIG.render("CONNECTION OK", True, WHITE)
    elif status == "FAIL":
        x_center = (panel_x + 80, panel_y + panel_height // 2)
        pygame.draw.circle(screen, WHITE, x_center, 45, 6)
        pygame.draw.line(screen, WHITE, (x_center[0] - 15, x_center[1] - 15),
                         (x_center[0] + 15, x_center[1] + 15), 8)
        pygame.draw.line(screen, WHITE, (x_center[0] + 15, x_center[1] - 15),
                         (x_center[0] - 15, x_center[1] + 15), 8)
        result_txt = BIG.render("CABLE FAULT", True, WHITE)
    else:
        result_txt = TITLE_FONT.render("Ready to Test", True, DARK_GRAY)

    txt_rect = result_txt.get_rect(center=(panel_x + panel_width // 2 + 60, panel_y + panel_height // 2))
    screen.blit(result_txt, txt_rect)

# -----------------------------
# MAIN LOOP
# -----------------------------
setup_gpio()
connections = {}
test_mode = "STRAIGHT"
last_button_state = GPIO.HIGH
button_pressed = False

while True:
    screen.fill(WHITE)

    # Read button
    current_button_state = GPIO.input(BUTTON_PIN)
    if current_button_state == GPIO.LOW and last_button_state == GPIO.HIGH:
        button_pressed = True
    last_button_state = current_button_state

    # Read switch
    switch_state = GPIO.input(SWITCH_PIN)
    test_mode = "STRAIGHT" if switch_state == GPIO.LOW else "CROSS"

    # Event handling
    mouse_pos = pygame.mouse.get_pos()
    test_btn_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 120, 200, 60)
    exit_btn_rect = pygame.Rect(WIDTH - 180, HEIGHT - 80, 150, 50)

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                cleanup()
                pygame.quit()
                sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if test_btn_rect.collidepoint(mouse_pos):
                button_pressed = True
            elif exit_btn_rect.collidepoint(mouse_pos):
                cleanup()
                pygame.quit()
                sys.exit()

    # Perform test
    if button_pressed:
        connections = scan_connections()
        button_pressed = False

    # Draw UI
    title = TITLE_FONT.render("CABLE TESTER PRO", True, BLACK)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))
    mode_color = BLUE if test_mode == "STRAIGHT" else ORANGE
    draw_status_badge(30, 30, f"MODE: {test_mode}", mode_color)

    left_positions = draw_pins(LEFT_X, "TX (Side A)")
    right_positions = draw_pins(RIGHT_X, "RX (Side B)")

    if connections:
        draw_connections(left_positions, right_positions, connections, test_mode)
        # Determine status
        if test_mode == "STRAIGHT":
            status = "PASS" if all(len(v) == 1 and v[0] == k for k, v in connections.items()) else "FAIL"
        else:
            status = "PASS" if all(len(v) == 1 and v[0] == CROSS_MAP[k] for k, v in connections.items()) else "FAIL"
        draw_result_panel(status)
    else:
        draw_result_panel("READY")

    # Draw buttons
    test_hover = test_btn_rect.collidepoint(mouse_pos)
    draw_button(WIDTH // 2 - 100, HEIGHT - 120, 200, 60, "TEST CABLE", ACCENT, test_hover)
    exit_hover = exit_btn_rect.collidepoint(mouse_pos)
    draw_button(WIDTH - 180, HEIGHT - 80, 150, 50, "EXIT", RED, exit_hover)

    pygame.display.flip()
