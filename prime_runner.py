# Fully playable console prototype: prime-driven infinite runner (turn-based)
# Controls:
#  - 'j' + Enter : jump
#  - '' (Enter)  : do nothing / advance frame
#  - 'q' + Enter : quit
#
# This is a simple, turn-based console prototype meant to run in this notebook or locally.
# It uses primes to generate chunks on the fly. Each new prime generates a chunk appended to the world.
# The viewport scrolls from left to right; the player is always at a fixed x within the viewport.
#
# To stop the game, press 'q' and Enter.
#
# Note: This is a console (text) prototype. For a smoother real-time game, port to Pygame/Unity/Godot.
import math, sys, time, random

# ---------- Prime generator (incremental using trial division with primes list) ----------
_primes = [2]
def next_prime():
    """Return the next prime after the current largest in _primes and append it."""
    candidate = _primes[-1] + 1
    while True:
        is_p = True
        limit = int(math.sqrt(candidate)) + 1
        for pr in _primes:
            if pr > limit:
                break
            if candidate % pr == 0:
                is_p = False
                break
        if is_p:
            _primes.append(candidate)
            return candidate
        candidate += 1

# ---------- prime_event from earlier, slightly adjusted to accept prev_prime for twin detection ----------
def prime_event(p, prev_prime=None):
    events = {}
    events["height_offset"] = (p % 7) - 3
    events["spacing"] = (p % 10) + 4        # shorter spacing for playability in console
    events["chunk_length"] = (p % 30) + 20  # width of chunk
    obstacles = []
    if p % 3 == 0:
        obstacles.append("cactus")
    if p % 5 == 0:
        obstacles.append("pit")
    if p % 7 == 0:
        obstacles.append("flying_enemy")
    if p % 11 == 0:
        obstacles.append("tall_obstacle")
    if not obstacles:
        obstacles.append("small_bump")
    events["obstacles"] = obstacles
    powerups = []
    if p % 13 == 0:
        powerups.append("double_jump")
    if p % 17 == 0:
        powerups.append("shield")
    if p % 19 == 0:
        powerups.append("slow_time")
    events["powerups"] = powerups
    events["theme_change"] = None
    if p % 41 == 0:
        events["theme_change"] = "night"
    elif p % 43 == 0:
        events["theme_change"] = "rain"
    elif p % 47 == 0:
        events["theme_change"] = "sandstorm"
    events["special"] = None
    # twin prime detection
    if prev_prime is not None and abs(p - prev_prime) == 2:
        events["special"] = "twin_boost"
    # mersenne-ish check (simple)
    if (p + 1) & p == 0:
        events["special"] = "mersenne_bonus"
    return events

# ---------- chunk generator (returns a list of strings rows) ----------
def generate_chunk(params, base_ground=8, width_override=None):
    width = width_override or params["chunk_length"]
    height = base_ground + 6
    grid = [[" " for _ in range(width)] for _ in range(height)]
    ground_y = base_ground + params["height_offset"]
    ground_y = max(3, min(height - 2, ground_y))
    for x in range(width):
        grid[ground_y][x] = "_"
        for y in range(ground_y + 1, height):
            grid[y][x] = "█"
    spacing = params["spacing"]
    obstacles = params["obstacles"]
    x = spacing % max(3, width - 2)
    if x < 2:
        x = 2
    for obst in obstacles:
        if x >= width - 1:
            break
        if obst == "cactus":
            grid[ground_y - 1][x] = "♣"
        elif obst == "pit":
            for dx in range(2):
                if x + dx < width:
                    grid[ground_y][x + dx] = " "
                    for y in range(ground_y + 1, height):
                        grid[y][x + dx] = " "
        elif obst == "tall_obstacle":
            grid[ground_y - 1][x] = "│"
            if ground_y - 2 >= 0:
                grid[ground_y - 2][x] = "│"
        elif obst == "flying_enemy":
            fly_y = max(1, ground_y - 3)
            grid[fly_y][x] = "✈"
        elif obst == "small_bump":
            grid[ground_y - 1][x] = "▲"
        x += spacing
    # powerups
    for i, pwr in enumerate(params["powerups"]):
        px = min(width - 3, 3 + i*4)
        py = ground_y - 2
        if pwr == "double_jump":
            grid[py][px] = "⬡"
        elif pwr == "shield":
            grid[py][px] = "◎"
        elif pwr == "slow_time":
            grid[py][px] = "⧗"
    # theme indicator
    if params["theme_change"]:
        tag = {"night":"N","rain":"R","sandstorm":"S"}[params["theme_change"]]
        grid[0][0] = tag
    return ["".join(row) for row in grid]

# ---------- Helper to stitch chunks into an infinite world list of columns ----------
def append_chunk_to_world(world_cols, chunk_rows):
    # world_cols: list of columns (each column is string of height), chunk_rows: list of rows (strings)
    height = len(chunk_rows)
    width = len(chunk_rows[0])
    for x in range(width):
        col = "".join(chunk_rows[y][x] for y in range(height))
        world_cols.append(col)

# ---------- Simple renderer for a viewport ----------
def render_viewport(world_cols, camera_x, view_w=40, view_h=14, player_x_rel=8, player_y=None, score=0):
    # camera_x: index in world_cols where viewport starts
    view_w = min(view_w, max(10, len(world_cols) - camera_x))
    view_cols = world_cols[camera_x:camera_x+view_w]
    # Each col is a string of height
    height = len(view_cols[0])
    rows = [[" " for _ in range(view_w)] for _ in range(height)]
    for cx, col in enumerate(view_cols):
        for y, ch in enumerate(col):
            rows[y][cx] = ch
    # place player
    if player_y is not None:
        px = player_x_rel
        if 0 <= px < view_w and 0 <= player_y < height:
            rows[player_y][px] = "P"
    # join
    lines = ["".join(row) for row in rows]
    header = f"Score: {score}  Primes found: {len(_primes)}  Next prime preview hidden.  Controls: j=jump, q=quit, Enter=wait"
    sep = "-" * min(120, view_w)
    return "\n".join([header, sep] + lines + [sep])

# ---------- Collision detection ----------
def is_solid_at(world_cols, x_global, y):
    if x_global >= len(world_cols) or x_global < 0:
        return False
    col = world_cols[x_global]
    if y < 0 or y >= len(col):
        return False
    ch = col[y]
    return ch not in (" ",)

# ---------- Build initial world with a few primes ----------
world_cols = []
for i in range(3):  # seed with a few primes/chunks
    p = next_prime()
    params = prime_event(p, _primes[-2] if len(_primes)>=2 else None)
    chunk = generate_chunk(params)
    append_chunk_to_world(world_cols, chunk)

# ---------- Game state ----------
camera_x = 0
viewport_w = 40
viewport_h = len(world_cols[0])
player_x_rel = 8  # player's column in viewport
player_global_x = player_x_rel  # will increase as camera moves
base_ground_guess = 10
player_y = 0
vy = 0.0
gravity = 1.0
on_ground = False
jump_strength = -4.0
score = 0
double_jump_available = False
shield = False
slow_time_turns = 0
game_over = False
ticks = 0

# Initialize player on top of ground at starting column
# find first ground column under player_global_x
def find_ground_y(world_cols, x):
    col = world_cols[x] if x < len(world_cols) else None
    if not col:
        return base_ground_guess
    # ground is first underscore from top
    for y, ch in enumerate(col):
        if ch == "_":
            return y
    return base_ground_guess

player_y = find_ground_y(world_cols, player_global_x) - 1
on_ground = True

# ---------- Main loop (turn-based) ----------
print("Prime Runner - console prototype. Press Enter each frame. 'j' + Enter to jump. 'q' + Enter to quit.")
while not game_over:
    # Ensure enough world ahead; generate primes/chunks as needed
    while len(world_cols) < camera_x + viewport_w + 40:
        prev_p = _primes[-1] if _primes else None
        p = next_prime()
        params = prime_event(p, prev_p)
        chunk = generate_chunk(params)
        append_chunk_to_world(world_cols, chunk)

    # render
    out = render_viewport(world_cols, camera_x, view_w=viewport_w, view_h=viewport_h, player_x_rel=player_x_rel, player_y=player_y, score=score)
    print("\033[H\033[J", end="")  # clear screen
    print(out)

    # get input
    cmd = input("Command (j=jump, q=quit, Enter=wait): ").strip().lower()
    if cmd == "q":
        print("Quitting...")
        break
    do_jump = (cmd == "j")

    # handle jump (simple)
    if do_jump:
        if on_ground:
            vy = jump_strength
            on_ground = False
            double_jump_available = True
        elif double_jump_available:
            vy = jump_strength
            double_jump_available = False

    # physics update (discrete)
    vy += gravity
    new_y = int(player_y + vy)
    # prevent falling below bottom
    max_y = viewport_h - 1
    if new_y > max_y:
        new_y = max_y
        vy = 0
    # collision with ground: find ground y at player's global x
    global_x = camera_x + player_x_rel
    ground_y = None
    # look for underscore in column
    col = world_cols[global_x]
    for y, ch in enumerate(col):
        if ch == "_":
            ground_y = y
            break
    if ground_y is None:
        ground_y = viewport_h - 2
    # if falling onto ground
    if new_y >= ground_y - 1:
        player_y = ground_y - 1
        vy = 0
        on_ground = True
    else:
        player_y = new_y
        on_ground = False

    # collision with obstacles at player's position
    # check the cell at player's location in the world
    cell_ch = world_cols[global_x][player_y]
    if cell_ch in ("♣","│","▲"):  # hitting obstacle
        if shield:
            shield = False
            print("Shield used to block obstacle!")
        else:
            print("\nYou hit an obstacle! Game Over.")
            game_over = True
            break
    elif cell_ch == " ":
        # in the air or falling into a pit: check below
        below_y = player_y + 1
        if below_y >= len(world_cols[global_x]) or world_cols[global_x][below_y] == " ":
            # falling into pit
            print("\nYou fell into a pit! Game Over.")
            game_over = True
            break
    elif cell_ch == "✈":
        # collision with flying enemy if at same y
        if shield:
            shield = False
        else:
            print("\nHit by flying enemy! Game Over.")
            game_over = True
            break
    elif cell_ch in ("⬡","◎","⧗"):
        # pick up power-up
        if cell_ch == "⬡":
            double_jump_available = True
            print("Picked up double-jump!")
        elif cell_ch == "◎":
            shield = True
            print("Picked up shield!")
        elif cell_ch == "⧗":
            slow_time_turns = 3
            print("Picked up slow-time!")
        # remove powerup from world by replacing that char with space in column
        col_list = list(world_cols[global_x])
        col_list[player_y] = " "
        world_cols[global_x] = "".join(col_list)

    # advance camera (movement)
    advance = 1
    if slow_time_turns > 0:
        advance = 0  # slow time freezes forward movement for a turn
        slow_time_turns -= 1
    camera_x += advance
    score += 1
    ticks += 1

print(f"Final score: {score}, Primes generated: {len(_primes)}")
