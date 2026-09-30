"""Hand Flappy Bird - control the bird with your index finger.

Setup:  pip install opencv-python mediapipe pygame
Run:    python hand_flappy_bird.py
Keys:   SPACE = start, ESC = quit
"""
import random
import cv2
import pygame
import mediapipe as mp

W, H = 960, 540
DURATION = 60          # round length in seconds
LIVES = 3
BX, R = 220, 18        # bird x position and radius
PIPE_W = 60
BEST_FILE = "best_score.txt"

# ---------- setup ----------
pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Hand Flappy Bird")
clock = pygame.time.Clock()
f_small = pygame.font.SysFont("arial", 26, bold=True)
f_mid = pygame.font.SysFont("arial", 38, bold=True)
f_big = pygame.font.SysFont("arial", 70, bold=True)

cap = cv2.VideoCapture(0)
hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.6,
                                 min_tracking_confidence=0.5)

try:
    best = int(open(BEST_FILE).read())
except Exception:
    best = 0


def text(s, font, color, x, y, align="center"):
    img = font.render(s, True, color)
    rect = img.get_rect()
    setattr(rect, {"center": "center", "left": "topleft", "right": "topright"}[align], (x, y))
    if align == "center":
        rect.center = (x, y)
    screen.blit(img, rect)


def read_hand():
    """Returns (hand_y_in_screen_pixels or None, preview_surface)."""
    ok, frame = cap.read()
    if not ok:
        return None, None
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands.process(rgb)
    hand_y = None
    if res.multi_hand_landmarks:
        tip = res.multi_hand_landmarks[0].landmark[8]           # index fingertip
        norm = min(1.0, max(0.0, (tip.y - 0.15) / 0.7))         # use the middle band of the camera
        hand_y = norm * H
        cv2.circle(rgb, (int(tip.x * rgb.shape[1]), int(tip.y * rgb.shape[0])), 10, (255, 0, 0), -1)
    small = cv2.resize(rgb, (200, 150))
    return hand_y, pygame.image.frombuffer(small.tobytes(), (200, 150), "RGB")


# ---------- game state ----------
state = "ready"        # ready, countdown, playing, over
bird_y = H / 2
pipes, score, lives, time_left, spawn_t, invuln = [], 0, LIVES, DURATION, 0, 0
countdown, over_at = 3, 0


def reset():
    global pipes, score, lives, time_left, spawn_t, invuln, bird_y
    pipes, score, lives, time_left, spawn_t, invuln, bird_y = [], 0, LIVES, DURATION, 0, 0, H / 2


def spawn_pipe():
    gap = 210 - (DURATION - time_left) * 0.9        # gap tightens over time
    top = random.randint(60, int(H - gap - 60))
    pipes.append({"x": W + 40, "top": top, "gap": gap, "passed": False})


# ---------- main loop ----------
running = True
while running:
    dt = min(0.05, clock.tick(60) / 1000)
    for e in pygame.event.get():
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            running = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE and state == "ready":
            reset()
            state, countdown = "countdown", 3

    hand_y, preview = read_hand()
    if hand_y is not None:
        bird_y += (hand_y - bird_y) * min(1, dt * 12)   # smooth following
    bird_y = min(H - R, max(R, bird_y))

    if state == "countdown":
        countdown -= dt
        if countdown <= 0:
            state = "playing"

    elif state == "playing":
        time_left -= dt
        invuln = max(0, invuln - dt)
        spawn_t -= dt
        if spawn_t <= 0:
            spawn_pipe()
            spawn_t = 1.5
        speed = 230 + (DURATION - time_left) * 2
        for p in pipes:
            p["x"] -= speed * dt
            if not p["passed"] and p["x"] + PIPE_W < BX - R:
                p["passed"] = True
                score += 1
            hit = (BX + R > p["x"] and BX - R < p["x"] + PIPE_W and
                   (bird_y - R < p["top"] or bird_y + R > p["top"] + p["gap"]))
            if hit and invuln == 0:
                lives -= 1
                invuln = 1.2
                if lives <= 0:
                    time_left = 0
        pipes = [p for p in pipes if p["x"] > -80]
        if time_left <= 0:
            state, over_at = "over", pygame.time.get_ticks()
            if score > best:
                best = score
                open(BEST_FILE, "w").write(str(best))

    elif state == "over" and pygame.time.get_ticks() - over_at > 8000:
        state = "ready"

    # ---------- draw ----------
    screen.fill((110, 200, 240))
    for p in pipes:
        pygame.draw.rect(screen, (67, 160, 71), (p["x"], 0, PIPE_W, p["top"]))
        pygame.draw.rect(screen, (67, 160, 71), (p["x"], p["top"] + p["gap"], PIPE_W, H))
        pygame.draw.rect(screen, (46, 125, 50), (p["x"] - 5, p["top"] - 24, PIPE_W + 10, 24))
        pygame.draw.rect(screen, (46, 125, 50), (p["x"] - 5, p["top"] + p["gap"], PIPE_W + 10, 24))

    if not (invuln > 0 and int(invuln * 10) % 2):        # blink while invulnerable
        pygame.draw.circle(screen, (255, 235, 59), (BX, int(bird_y)), R)
        pygame.draw.circle(screen, (255, 255, 255), (BX + 7, int(bird_y) - 5), 6)
        pygame.draw.circle(screen, (0, 0, 0), (BX + 9, int(bird_y) - 5), 3)
        pygame.draw.polygon(screen, (255, 112, 67),
                            [(BX + 16, bird_y), (BX + 30, bird_y + 4), (BX + 16, bird_y + 8)])

    if state in ("countdown", "playing", "over"):
        text(f"Score {score}", f_mid, (255, 255, 255), 20, 15, "left")
        text("<3 " * max(0, lives), f_small, (229, 57, 53), 20, 60, "left")
        text(f"{max(0, int(time_left + 0.99))}s", f_mid, (255, 255, 255), W - 20, 15, "right")
    if state == "playing" and hand_y is None:
        text("Show your hand!", f_small, (255, 235, 59), W // 2, 40)

    if state != "playing":
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 140))
        screen.blit(shade, (0, 0))
    if state == "ready":
        text("HAND FLAPPY BIRD", f_big, (255, 255, 255), W // 2, 170)
        text("Move your index finger up and down to fly", f_small, (255, 255, 255), W // 2, 240)
        text("Pass pipes for points. 3 lives. 60 seconds.", f_small, (255, 255, 255), W // 2, 280)
        msg = "Raise your hand to the camera..." if hand_y is None else "Hand detected! Press SPACE to start"
        text(msg, f_small, (255, 235, 59), W // 2, 350)
        text(f"Best: {best}", f_small, (255, 255, 255), W // 2, 410)
    elif state == "countdown":
        text(str(int(countdown) + 1), f_big, (255, 255, 255), W // 2, H // 2)
    elif state == "over":
        text("TIME'S UP!", f_big, (255, 255, 255), W // 2, 190)
        text(f"Score: {score}", f_mid, (255, 235, 59), W // 2, 275)
        text(f"Best: {best}", f_small, (255, 255, 255), W // 2, 330)
        wait = max(0, 8 - (pygame.time.get_ticks() - over_at) // 1000)
        text(f"Next player in {wait}...", f_small, (255, 255, 255), W // 2, 400)

    if preview:
        screen.blit(preview, (W - 210, H - 160))
    pygame.display.flip()

cap.release()
pygame.quit()