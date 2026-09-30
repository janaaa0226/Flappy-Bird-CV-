"""Hand Flappy Bird v2 - control the bird with your index finger.

Setup:  pip install opencv-python mediapipe pygame
Run:    python hand_flappy_bird_v2.py      (SPACE = start, ESC = quit)

New: combo multiplier (fly through the CENTER of gaps), coins, particles,
screen shake, wavy pipes after 15s, and a x2 FRENZY in the last 10 seconds.
"""
import math, random
import cv2, pygame
import mediapipe as mp

W, H = 960, 540
DURATION, LIVES, BX, R, PIPE_W = 60, 3, 220, 18, 60
BEST_FILE = "best_flappy.txt"

pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Hand Flappy Bird v2")
clock = pygame.time.Clock()
F_S = pygame.font.SysFont("arial", 26, bold=True)
F_M = pygame.font.SysFont("arial", 38, bold=True)
F_B = pygame.font.SysFont("arial", 70, bold=True)
world = pygame.Surface((W, H))

cap = cv2.VideoCapture(0)
hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.5)
try:
    best = int(open(BEST_FILE).read())
except Exception:
    best = 0
clouds = [[random.randint(0, W), random.randint(20, 300), random.randint(40, 90), random.uniform(15, 40)] for _ in range(7)]


def text(s, font, color, x, y, align="center", surf=None):
    img = font.render(s, True, color)
    r = img.get_rect()
    if align == "center": r.center = (x, y)
    elif align == "left": r.topleft = (x, y)
    else: r.topright = (x, y)
    (surf or screen).blit(img, r)


def read_hand():
    ok, frame = cap.read()
    if not ok: return None, None
    rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
    res = hands.process(rgb)
    y = None
    if res.multi_hand_landmarks:
        tip = res.multi_hand_landmarks[0].landmark[8]
        y = min(1.0, max(0.0, (tip.y - 0.15) / 0.7)) * H
        cv2.circle(rgb, (int(tip.x * rgb.shape[1]), int(tip.y * rgb.shape[0])), 10, (255, 0, 0), -1)
    small = cv2.resize(rgb, (200, 150))
    return y, pygame.image.frombuffer(small.tobytes(), (200, 150), "RGB")


state, bird_y = "ready", H / 2
pipes, parts, floats, trail = [], [], [], []
score = lives = 0
time_left = DURATION
spawn_t = invuln = shake = flash = 0.0
combo, countdown, over_at, tt = 0, 3, 0, 0.0


def reset():
    global pipes, parts, floats, trail, score, lives, time_left, spawn_t, invuln, shake, flash, combo, bird_y
    pipes, parts, floats, trail = [], [], [], []
    score, lives, time_left, spawn_t, invuln, shake, flash, combo, bird_y = 0, LIVES, DURATION, 0, 0, 0, 0, 0, H / 2


def burst(x, y, color, n=16):
    for _ in range(n):
        a, s = random.uniform(0, 6.28), random.uniform(60, 260)
        parts.append([x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.4, 0.9), color])


def pipe_top(p):
    off = 0
    if DURATION - time_left > 15:
        off = math.sin(tt * 2.2 + p["ph"]) * min(60, (DURATION - time_left - 15) * 4)
    return max(40, min(H - p["gap"] - 40, p["base"] + off))


def mult():
    return (1 + min(4, combo // 2)) * (2 if time_left <= 10 else 1)


running = True
while running:
    dt = min(0.05, clock.tick(60) / 1000)
    tt += dt
    for e in pygame.event.get():
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE): running = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE and state == "ready":
            reset(); state, countdown = "countdown", 3

    hand_y, preview = read_hand()
    if hand_y is not None: bird_y += (hand_y - bird_y) * min(1, dt * 12)
    bird_y = min(H - R, max(R, bird_y))

    if state == "countdown":
        countdown -= dt
        if countdown <= 0: state = "playing"
    elif state == "playing":
        time_left -= dt
        invuln, shake, flash = max(0, invuln - dt), max(0, shake - dt * 30), max(0, flash - dt * 3)
        spawn_t -= dt
        if spawn_t <= 0:
            gap = 215 - (DURATION - time_left) * 0.9
            pipes.append({"x": W + 40, "base": random.randint(70, int(H - gap - 70)), "gap": gap,
                          "ph": random.uniform(0, 6), "passed": False, "coin": random.random() < 0.6, "got": False})
            spawn_t = 1.4
        speed = (230 + (DURATION - time_left) * 2.5) * (1.2 if time_left <= 10 else 1)
        trail.append([BX, bird_y, 0.4])
        for p in pipes:
            p["x"] -= speed * dt
            top = pipe_top(p)
            mid = top + p["gap"] / 2
            if not p["passed"] and p["x"] + PIPE_W < BX - R:
                p["passed"] = True
                if abs(bird_y - mid) < p["gap"] * 0.25:
                    combo += 1
                    floats.append([f"PERFECT x{mult()}" if combo > 1 else "PERFECT", BX + 60, bird_y - 30, 1.0, (255, 235, 59)])
                else:
                    combo = 0
                score += mult()
                burst(BX, bird_y, (255, 255, 255), 6)
            if p["coin"] and not p["got"] and math.hypot(p["x"] + PIPE_W / 2 - BX, mid - bird_y) < R + 16:
                p["got"] = True
                score += 5 * mult()
                burst(BX, bird_y, (255, 215, 0), 20)
                floats.append([f"+{5 * mult()}", BX + 40, bird_y - 20, 0.8, (255, 215, 0)])
            hit = BX + R > p["x"] and BX - R < p["x"] + PIPE_W and (bird_y - R < top or bird_y + R > top + p["gap"])
            if hit and invuln == 0:
                lives -= 1; invuln, shake, flash, combo = 1.2, 14, 1.0, 0
                burst(BX, bird_y, (255, 80, 60), 30)
                if lives <= 0: time_left = 0
        pipes = [p for p in pipes if p["x"] > -80]
        if time_left <= 0:
            state, over_at = "over", pygame.time.get_ticks()
            if score > best:
                best = score
                open(BEST_FILE, "w").write(str(best))
    elif state == "over" and pygame.time.get_ticks() - over_at > 8000:
        state = "ready"

    for c in clouds:
        c[0] -= c[3] * dt
        if c[0] < -100: c[0], c[1] = W + 100, random.randint(20, 300)
    for pt in parts:
        pt[0] += pt[2] * dt; pt[1] += pt[3] * dt; pt[4] -= dt
    parts[:] = [pt for pt in parts if pt[4] > 0]
    for t in trail: t[0] -= 230 * dt; t[2] -= dt
    trail[:] = [t for t in trail if t[2] > 0]
    for f in floats: f[1] += 0; f[2] -= 40 * dt; f[3] -= dt
    floats[:] = [f for f in floats if f[3] > 0]

    # ---- draw world ----
    frenzy = state == "playing" and time_left <= 10
    top_c, bot_c = ((255, 120, 90), (255, 200, 150)) if frenzy else ((79, 195, 247), (179, 229, 252))
    for i in range(0, H, 6):
        k = i / H
        world.fill(tuple(int(top_c[j] + (bot_c[j] - top_c[j]) * k) for j in range(3)), (0, i, W, 6))
    for c in clouds:
        pygame.draw.ellipse(world, (255, 255, 255), (c[0], c[1], c[2] * 1.6, c[2] * 0.6))
    for p in pipes:
        top = pipe_top(p)
        for rect, cap_rect in (((p["x"], 0, PIPE_W, top), (p["x"] - 5, top - 24, PIPE_W + 10, 24)),
                               ((p["x"], top + p["gap"], PIPE_W, H), (p["x"] - 5, top + p["gap"], PIPE_W + 10, 24))):
            pygame.draw.rect(world, (67, 160, 71), rect)
            pygame.draw.rect(world, (46, 125, 50), cap_rect)
        if p["coin"] and not p["got"]:
            cy = top + p["gap"] / 2 + math.sin(tt * 6 + p["ph"]) * 6
            pygame.draw.circle(world, (255, 215, 0), (int(p["x"] + PIPE_W / 2), int(cy)), 14)
            pygame.draw.circle(world, (200, 160, 0), (int(p["x"] + PIPE_W / 2), int(cy)), 14, 3)
    for t in trail:
        pygame.draw.circle(world, (255, 245, 157), (int(t[0]), int(t[1])), int(R * t[2] * 2))
    if not (invuln > 0 and int(invuln * 10) % 2):
        wing = math.sin(tt * 18) * 8
        pygame.draw.circle(world, (255, 235, 59), (BX, int(bird_y)), R)
        pygame.draw.ellipse(world, (255, 193, 7), (BX - 14, bird_y + wing - 4, 18, 10))
        pygame.draw.circle(world, (255, 255, 255), (BX + 7, int(bird_y) - 5), 6)
        pygame.draw.circle(world, (0, 0, 0), (BX + 9, int(bird_y) - 5), 3)
        pygame.draw.polygon(world, (255, 112, 67), [(BX + 16, bird_y), (BX + 30, bird_y + 4), (BX + 16, bird_y + 8)])
    for pt in parts:
        pygame.draw.circle(world, pt[5], (int(pt[0]), int(pt[1])), max(1, int(pt[4] * 6)))
    ox, oy = (random.uniform(-shake, shake), random.uniform(-shake, shake)) if shake else (0, 0)
    screen.blit(world, (ox, oy))
    if flash > 0:
        red = pygame.Surface((W, H), pygame.SRCALPHA); red.fill((255, 0, 0, int(120 * flash))); screen.blit(red, (0, 0))

    # ---- HUD ----
    if state in ("countdown", "playing", "over"):
        text(f"Score {score}", F_M, (255, 255, 255), 20, 15, "left")
        text("<3 " * max(0, lives), F_S, (229, 57, 53), 20, 60, "left")
        text(f"{max(0, int(time_left + 0.99))}s", F_M, (255, 255, 255), W - 20, 15, "right")
        if state == "playing" and mult() > 1:
            text(f"x{mult()}", F_M, (255, 235, 59), W // 2, 30)
        if frenzy:
            text("FRENZY! DOUBLE POINTS", F_S, (255, 255, 255), W // 2, 75)
    for f in floats:
        text(f[0], F_S, f[4], int(f[1]), int(f[2]))
    if state == "playing" and hand_y is None:
        text("Show your hand!", F_S, (255, 235, 59), W // 2, 110)

    if state != "playing":
        sh = pygame.Surface((W, H), pygame.SRCALPHA); sh.fill((0, 0, 0, 140)); screen.blit(sh, (0, 0))
    if state == "ready":
        text("HAND FLAPPY BIRD", F_B, (255, 255, 255), W // 2, 150)
        for i, s in enumerate(["Move your index finger up and down to fly",
                               "Fly through the CENTER of gaps to build a combo",
                               "Grab coins. Last 10 seconds = double points!"]):
            text(s, F_S, (255, 255, 255), W // 2, 230 + i * 38)
        text("Raise your hand to the camera..." if hand_y is None else "Hand detected! Press SPACE to start",
             F_S, (255, 235, 59), W // 2, 380)
        text(f"Best: {best}", F_S, (255, 255, 255), W // 2, 430)
    elif state == "countdown":
        text(str(int(countdown) + 1), F_B, (255, 255, 255), W // 2, H // 2)
    elif state == "over":
        text("TIME'S UP!", F_B, (255, 255, 255), W // 2, 190)
        text(f"Score: {score}", F_M, (255, 235, 59), W // 2, 275)
        text("NEW BEST!" if score >= best and score > 0 else f"Best: {best}", F_S, (255, 255, 255), W // 2, 330)
        text(f"Next player in {max(0, 8 - (pygame.time.get_ticks() - over_at) // 1000)}...", F_S, (255, 255, 255), W // 2, 400)
    if preview: screen.blit(preview, (W - 210, H - 160))
    pygame.display.flip()

cap.release()
pygame.quit()