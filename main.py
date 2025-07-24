import pygame
import heapq
import sys
import math
import random

# --- Setup ---
pygame.init()
WIDTH, HEIGHT = 1280, 720
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AI Car Final | Smart Rerouting AI")

# --- Constants ---
# Colors
BLACK, WHITE, RED = (0, 0, 0), (255, 255, 255), (200, 0, 0)
PATH_BLUE, YELLOW, ORANGE = (0, 150, 255), (255, 255, 0), (255, 165, 0)
# Grid & World
GRID_SIZE = 40
ROWS, COLS = 50, 80
WORLD_WIDTH, WORLD_HEIGHT = COLS * GRID_SIZE, ROWS * GRID_SIZE
# Car
CAR_SPEED = 3.5
ARRIVAL_DISTANCE = 10.0
# Camera
MAX_ZOOM, MIN_ZOOM = 5.0, 0.1
# Traffic
TRAFFIC_GENERATION_INTERVAL = 200 # ms
TRAFFIC_LIFESPAN = 20000 # ms
MAX_TRAFFIC_STOPS = 60
# AI Behavior
PROACTIVE_REROUTE_INTERVAL = 500 # ms (car checks for a better path every half-second)

# --- Assets ---
CAR_IMG = pygame.transform.scale(pygame.image.load("red_car.png"), (35, 70))
MARKER_IMG = pygame.transform.scale(pygame.image.load("location_drop.png"), (30, 30))

# --- World Generation ---
grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
def generate_houses(count):
    for _ in range(count):
        while True:
            r, c = random.randint(0, ROWS-1), random.randint(0, COLS-1)
            if grid[r][c] == 0 and not (c < 5 and r > ROWS-5): grid[r][c] = 1; break
generate_houses(400)

WORLD_SURFACE = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
WORLD_SURFACE.fill(BLACK)
for r in range(ROWS):
    for c in range(COLS):
        if grid[r][c] == 1: pygame.draw.rect(WORLD_SURFACE, WHITE, (c*GRID_SIZE, r*GRID_SIZE, GRID_SIZE, GRID_SIZE))

# --- Game State Variables ---
# These are grouped together in a dictionary for cleaner management
state = {
    "car_x": 200, "car_y": WORLD_HEIGHT - 200, "car_angle": 0,
    "car_path": [], "destination": None,
    "car_is_waiting": False, "car_wait_end_time": 0,
    "camera_x": 0, "camera_y": 0, "camera_zoom": 1.0, "camera_mode": "free",
    "traffic_stops": {}, "last_traffic_gen_time": 0, "last_reroute_check": 0
}

# --- Core Functions ---
def a_star(start, goal, traffic_stops):
    """A* pathfinding that considers 10-second traffic as obstacles."""
    queue, came_from, cost_so_far = [], {start: None}, {start: 0}
    heapq.heappush(queue, (0, start))
    while queue:
        _, current = heapq.heappop(queue)
        if current == goal: break
        x, y = current
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x + dx, y + dy
            is_reroute = traffic_stops.get((nx, ny), {}).get("type") == 10
            if 0<=nx<COLS and 0<=ny<ROWS and grid[ny][nx]==0 and not is_reroute:
                new_cost = cost_so_far[current] + 1
                if (nx,ny) not in cost_so_far or new_cost < cost_so_far[nx,ny]:
                    cost_so_far[nx,ny] = new_cost
                    priority = new_cost + abs(goal[0]-nx) + abs(goal[1]-ny)
                    heapq.heappush(queue, (priority, (nx,ny))); came_from[nx,ny] = current
    path = []
    if goal not in came_from: return []
    current = goal
    while current != start: path.append(current); current = came_from[current]
    path.reverse(); return path

def reset_simulation():
    """Resets the game state to its initial configuration."""
    global state
    state["car_path"], state["destination"], state["traffic_stops"] = [], None, {}
    state["camera_mode"] = "free"
    state["camera_zoom"] = min(WIDTH / WORLD_WIDTH, HEIGHT / WORLD_HEIGHT)
    state["camera_x"], state["camera_y"] = WORLD_WIDTH / 2, WORLD_HEIGHT / 2
    print("Simulation Reset!")

# --- Main Game Loop Functions ---

def handle_input(events, state, mouse_pos, pan_state):
    """Handles all user input and updates the game state accordingly."""
    for event in events:
        if event.type == pygame.QUIT: return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r: reset_simulation()
        
        # --- Camera Control ---
        if event.type == pygame.MOUSEWHEEL:
            state["camera_mode"] = "free"
            world_x = (mouse_pos[0]-WIDTH/2)/state["camera_zoom"] + state["camera_x"]
            world_y = (mouse_pos[1]-HEIGHT/2)/state["camera_zoom"] + state["camera_y"]
            state["camera_zoom"] *= 1.1 if event.y > 0 else 1/1.1
            state["camera_zoom"] = max(MIN_ZOOM, min(state["camera_zoom"], MAX_ZOOM))
            state["camera_x"] = world_x - (mouse_pos[0]-WIDTH/2)/state["camera_zoom"]
            state["camera_y"] = world_y - (mouse_pos[1]-HEIGHT/2)/state["camera_zoom"]
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            state["camera_mode"] = "free"
            pan_state["is_panning"] = True
            pan_state["start_pos"] = mouse_pos
        
        if event.type == pygame.MOUSEMOTION and pan_state["is_panning"]:
            dx, dy = mouse_pos[0]-pan_state["start_pos"][0], mouse_pos[1]-pan_state["start_pos"][1]
            state["camera_x"] -= dx / state["camera_zoom"]
            state["camera_y"] -= dy / state["camera_zoom"]
            pan_state["start_pos"] = mouse_pos
            
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if pan_state["is_panning"] and math.hypot(mouse_pos[0]-pan_state["click_down_pos"][0], mouse_pos[1]-pan_state["click_down_pos"][1]) < 5:
                # This was a click, not a drag. Set destination.
                world_x = (mouse_pos[0]-WIDTH/2)/state["camera_zoom"] + state["camera_x"]
                world_y = (mouse_pos[1]-HEIGHT/2)/state["camera_zoom"] + state["camera_y"]
                c, r = int(world_x/GRID_SIZE), int(world_y/GRID_SIZE)
                if 0<=c<COLS and 0<=r<ROWS and grid[r][c]==0:
                    start_pos = (int(state["car_x"]/GRID_SIZE), int(state["car_y"]/GRID_SIZE))
                    state["destination"] = (c, r)
                    state["car_path"] = a_star(start_pos, state["destination"], state["traffic_stops"])
                    if not state["car_path"]:
                        state["destination"] = None; print("Path not found!")
                    else:
                        state["camera_mode"] = "follow"; state["car_is_waiting"] = False; print("Destination set!")
            pan_state["is_panning"] = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pan_state["click_down_pos"] = mouse_pos

    return True

def update_simulation(state, current_time):
    """Updates all game logic: traffic, AI, car movement, camera."""
    # --- Traffic ---
    if current_time - state["last_traffic_gen_time"] > TRAFFIC_GENERATION_INTERVAL:
        if len(state["traffic_stops"]) <= MAX_TRAFFIC_STOPS:
            while True:
                c,r = random.randint(0,COLS-1), random.randint(0,ROWS-1)
                if grid[r][c]==0 and (c,r) not in state["traffic_stops"]:
                    state["traffic_stops"][(c,r)] = {"type":random.choice([5,10,10]), "created":current_time}; break
        state["last_traffic_gen_time"] = current_time
    for pos in list(state["traffic_stops"].keys()):
        if current_time - state["traffic_stops"][pos]["created"] > TRAFFIC_LIFESPAN:
            del state["traffic_stops"][pos]

    # --- Car AI & Movement ---
    if state["destination"] and state["car_path"]:
        # Proactive Rerouting Check
        if current_time - state["last_reroute_check"] > PROACTIVE_REROUTE_INTERVAL:
            state["car_path"] = a_star((int(state["car_x"]/GRID_SIZE), int(state["car_y"]/GRID_SIZE)), state["destination"], state["traffic_stops"])
            state["last_reroute_check"] = current_time
            if not state["car_path"]: state["destination"] = None; print("Proactive check failed, stopping.")
        
        # Waiting Logic
        if state["car_is_waiting"]:
            if current_time >= state["car_wait_end_time"]: state["car_is_waiting"] = False
            return # Don't move if waiting

        # Traffic Interaction & Movement
        target = state["car_path"][0]
        if target in state["traffic_stops"]:
            if state["traffic_stops"][target]["type"] == 5:
                tx,ty = target[0]*GRID_SIZE+GRID_SIZE/2, target[1]*GRID_SIZE+GRID_SIZE/2
                if math.hypot(tx-state["car_x"], ty-state["car_y"]) < GRID_SIZE:
                    state["car_is_waiting"], state["car_wait_end_time"] = True, current_time + 5000
                    return # Start waiting, skip movement this frame

        # Normal Movement
        tx,ty = target[0]*GRID_SIZE+GRID_SIZE/2, target[1]*GRID_SIZE+GRID_SIZE/2
        dx,dy = tx-state["car_x"], ty-state["car_y"]
        dist = math.hypot(dx,dy)
        if dist < ARRIVAL_DISTANCE:
            state["car_path"].pop(0)
            if not state["car_path"]: state["destination"] = None
        else:
            state["car_angle"] = 90-math.degrees(math.atan2(-dy,dx))
            state["car_x"] += CAR_SPEED*dx/dist
            state["car_y"] += CAR_SPEED*dy/dist
    
    # --- Camera ---
    if state["camera_mode"] == "follow":
        state["camera_zoom"] += (1.0-state["camera_zoom"])*0.04
        state["camera_x"] += (state["car_x"]-state["camera_x"])*0.05
        state["camera_y"] += (state["car_y"]-state["camera_y"])*0.05

def render_scene(screen, surface, state):
    """Draws everything to the screen."""
    screen.fill(BLACK)
    
    # --- World & Scaled Objects ---
    cam_x, cam_y, zoom = state["camera_x"], state["camera_y"], state["camera_zoom"]
    scaled_w, scaled_h = int(WORLD_WIDTH*zoom), int(WORLD_HEIGHT*zoom)
    if scaled_w > 0 and scaled_h > 0:
        scaled_world = pygame.transform.scale(surface, (scaled_w, scaled_h))
        screen.blit(scaled_world, ((WIDTH/2)-(cam_x*zoom), (HEIGHT/2)-(cam_y*zoom)))

    # Draw traffic stops
    for (c, r), data in state["traffic_stops"].items():
        color = YELLOW if data["type"]==5 else ORANGE
        size = GRID_SIZE * zoom
        sx, sy = (c*GRID_SIZE-cam_x)*zoom+WIDTH/2, (r*GRID_SIZE-cam_y)*zoom+HEIGHT/2
        pygame.draw.rect(screen, color, (sx, sy, size, size))

    # Draw path
    if state["car_path"]:
        path_points = [((p[0]*GRID_SIZE+GRID_SIZE/2-cam_x)*zoom+WIDTH/2, (p[1]*GRID_SIZE+GRID_SIZE/2-cam_y)*zoom+HEIGHT/2) for p in state["car_path"]]
        if len(path_points)>1: pygame.draw.lines(screen, PATH_BLUE, False, path_points, max(1, int(3*zoom)))

    # Draw destination marker
    if state["destination"]:
        dx, dy = state["destination"][0]*GRID_SIZE+GRID_SIZE/2, state["destination"][1]*GRID_SIZE+GRID_SIZE/2
        sx, sy = (dx-cam_x)*zoom+WIDTH/2, (dy-cam_y)*zoom+HEIGHT/2
        mw, mh = int(30*zoom), int(30*zoom)
        if mw>0 and mh>0: screen.blit(pygame.transform.scale(MARKER_IMG, (mw,mh)), (sx-mw/2, sy-mh))
    
    # Draw car
    screen_x, screen_y = (state["car_x"]-cam_x)*zoom+WIDTH/2, (state["car_y"]-cam_y)*zoom+HEIGHT/2
    scaled_car = pygame.transform.scale(CAR_IMG, (int(35*zoom), int(70*zoom)))
    rotated = pygame.transform.rotate(scaled_car, state["car_angle"])
    screen.blit(rotated, rotated.get_rect(center=(screen_x, screen_y)))

    pygame.display.update()

def main():
    """Main game loop."""
    clock, running = pygame.time.Clock(), True
    reset_simulation()
    pan_state = {"is_panning": False, "start_pos": (0,0), "click_down_pos": (0,0)}

    while running:
        running = handle_input(pygame.event.get(), state, pygame.mouse.get_pos(), pan_state)
        update_simulation(state, pygame.time.get_ticks())
        render_scene(SCREEN, WORLD_SURFACE, state)
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()