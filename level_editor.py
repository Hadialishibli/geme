import pygame
import json

# --- Editor Settings ---
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TILE_SIZE = 64
EDITOR_FPS = 30

# Colors for visualization
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
GREEN = (0, 150, 0)
BLUE = (0, 0, 255)
BROWN = (139, 69, 19)
GREY = (128, 128, 128)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
PURPLE = (128, 0, 128) # For merchant
DARK_BROWN = (101, 67, 33) # For door
DARK_GREY = (50, 50, 50) # Keep this for grid lines

# --- Helper Functions ---
def load_level_data(filename):
    """Loads level data from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Level file '{filename}' not found. Creating a new one.")
        return {
            "map_width": 50, # Increased initial map size for infinite feeling
            "map_height": 50, # Increased initial map size
            "player_spawn": {"x": 1, "y": 1},
            "walls": [],
            "pots": [],
            "enemies": [],
            "merchants": [], # New: Merchants list
            "doors": []      # New: Doors list
        }
    except json.JSONDecodeError:
        print(f"Error: Could not parse '{filename}'. Check for syntax errors. Starting with empty data.")
        return {
            "map_width": 50, # Increased initial map size for infinite feeling
            "map_height": 50, # Increased initial map size
            "player_spawn": {"x": 1, "y": 1},
            "walls": [],
            "pots": [],
            "enemies": [],
            "merchants": [],
            "doors": []
        }

def save_level_data(filename, data):
    """Saves level data to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Level saved to {filename}")

# --- Editor Class ---
class LevelEditor:
    def __init__(self, level_file="level.json"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Level Editor")
        self.clock = pygame.time.Clock()
        self.level_file = level_file
        self.level_data = load_level_data(self.level_file)

        # These define the conceptual boundaries of the initially loaded map data,
        # but the editor camera can go beyond them.
        self.initial_map_width_tiles = self.level_data['map_width']
        self.initial_map_height_tiles = self.level_data['map_height']

        self.camera_x = 0
        self.camera_y = 0

        self.selected_tool = 'wall'  # 'wall', 'pot', 'enemy', 'player', 'merchant', 'door', 'erase'
        self.selected_item = None # For moving existing elements (not implemented yet, but good to have)

        self.running = True
        self.font = pygame.font.Font(None, 24)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Camera movement with arrow keys
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.camera_x += TILE_SIZE
                if event.key == pygame.K_RIGHT:
                    self.camera_x -= TILE_SIZE
                if event.key == pygame.K_UP:
                    self.camera_y += TILE_SIZE
                if event.key == pygame.K_DOWN:
                    self.camera_y -= TILE_SIZE
                
                # Tool selection
                if event.key == pygame.K_1:
                    self.selected_tool = 'wall'
                    print("Tool: Wall")
                if event.key == pygame.K_2:
                    self.selected_tool = 'pot'
                    print("Tool: Pot")
                if event.key == pygame.K_3:
                    self.selected_tool = 'enemy'
                    print("Tool: Enemy (Melee)")
                if event.key == pygame.K_4:
                    self.selected_tool = 'player'
                    print("Tool: Player Spawn")
                if event.key == pygame.K_5: # New hotkey for merchant
                    self.selected_tool = 'merchant'
                    print("Tool: Merchant")
                if event.key == pygame.K_6: # New hotkey for door
                    self.selected_tool = 'door'
                    print("Tool: Door")
                if event.key == pygame.K_e:
                    self.selected_tool = 'erase'
                    print("Tool: Erase")
                if event.key == pygame.K_s:
                    save_level_data(self.level_file, self.level_data)

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                # Convert screen coordinates to map coordinates (tile grid)
                map_x = (mouse_x - self.camera_x) // TILE_SIZE
                map_y = (mouse_y - self.camera_y) // TILE_SIZE

                if event.button == 1:  # Left click
                    if self.selected_tool == 'wall':
                        new_wall = {"x": int(map_x), "y": int(map_y), "w": 1, "h": 1}
                        if new_wall not in self.level_data['walls']:
                            self.level_data['walls'].append(new_wall)
                    elif self.selected_tool == 'pot':
                        new_pot = {"x": int(map_x), "y": int(map_y)}
                        if new_pot not in self.level_data['pots']:
                            self.level_data['pots'].append(new_pot)
                    elif self.selected_tool == 'enemy':
                        new_enemy = {"type": "melee", "x": int(map_x), "y": int(map_y)}
                        if new_enemy not in self.level_data['enemies']:
                            self.level_data['enemies'].append(new_enemy)
                    elif self.selected_tool == 'player':
                        self.level_data['player_spawn'] = {"x": int(map_x), "y": int(map_y)}
                    elif self.selected_tool == 'merchant': # New: Place merchant
                        new_merchant = {"x": int(map_x), "y": int(map_y)}
                        if new_merchant not in self.level_data['merchants']:
                            self.level_data['merchants'].append(new_merchant)
                    elif self.selected_tool == 'door': # New: Place door
                        new_door = {"x": int(map_x), "y": int(map_y)}
                        if new_door not in self.level_data['doors']:
                            self.level_data['doors'].append(new_door)
                    elif self.selected_tool == 'erase':
                        self.erase_at_position(map_x, map_y)

                elif event.button == 3:  # Right click (to remove elements)
                    self.erase_at_position(map_x, map_y)

    def erase_at_position(self, map_x, map_y):
        # Erase walls
        self.level_data['walls'] = [
            wall for wall in self.level_data['walls']
            if not (map_x >= wall['x'] and map_x < wall['x'] + wall['w'] and
                    map_y >= wall['y'] and map_y < wall['y'] + wall['h'])
        ]
        # Erase pots
        self.level_data['pots'] = [
            pot for pot in self.level_data['pots']
            if not (pot['x'] == map_x and pot['y'] == map_y)
        ]
        # Erase enemies
        self.level_data['enemies'] = [
            enemy for enemy in self.level_data['enemies']
            if not (enemy['x'] == map_x and enemy['y'] == map_y)
        ]
        # Erase merchants
        self.level_data['merchants'] = [ # New: Erase merchants
            merchant for merchant in self.level_data['merchants']
            if not (merchant['x'] == map_x and merchant['y'] == map_y)
        ]
        # Erase doors
        self.level_data['doors'] = [ # New: Erase doors
            door for door in self.level_data['doors']
            if not (door['x'] == map_x and door['y'] == map_y)
        ]
        # Reset player spawn if erased
        if self.level_data['player_spawn']['x'] == map_x and self.level_data['player_spawn']['y'] == map_y:
            self.level_data['player_spawn'] = {"x": 1, "y": 1} # Default spawn

    def draw(self):
        self.screen.fill(BLACK)

        # Draw grid for the visible area
        # Calculate the visible world coordinates
        visible_world_x_start = -self.camera_x
        visible_world_y_start = -self.camera_y
        visible_world_x_end = visible_world_x_start + SCREEN_WIDTH
        visible_world_y_end = visible_world_y_start + SCREEN_HEIGHT

        # Draw vertical grid lines
        for x in range(visible_world_x_start - (visible_world_x_start % TILE_SIZE), visible_world_x_end + TILE_SIZE, TILE_SIZE):
            screen_x = x + self.camera_x
            pygame.draw.line(self.screen, DARK_GREY, (screen_x, 0), (screen_x, SCREEN_HEIGHT))
        # Draw horizontal grid lines
        for y in range(visible_world_y_start - (visible_world_y_start % TILE_SIZE), visible_world_y_end + TILE_SIZE, TILE_SIZE):
            screen_y = y + self.camera_y
            pygame.draw.line(self.screen, DARK_GREY, (0, screen_y), (SCREEN_WIDTH, screen_y))


        # Draw walls
        for wall in self.level_data['walls']:
            pygame.draw.rect(self.screen, GREY, (wall['x'] * TILE_SIZE + self.camera_x,
                                                 wall['y'] * TILE_SIZE + self.camera_y,
                                                 wall['w'] * TILE_SIZE,
                                                 wall['h'] * TILE_SIZE))
        # Draw pots
        for pot in self.level_data['pots']:
            pygame.draw.rect(self.screen, BROWN, (pot['x'] * TILE_SIZE + self.camera_x,
                                                  pot['y'] * TILE_SIZE + self.camera_y,
                                                  TILE_SIZE, TILE_SIZE))
            text_surf = self.font.render("P", True, WHITE)
            self.screen.blit(text_surf, (pot['x'] * TILE_SIZE + self.camera_x + TILE_SIZE // 4,
                                         pot['y'] * TILE_SIZE + self.camera_y + TILE_SIZE // 4))

        # Draw enemies
        for enemy in self.level_data['enemies']:
            pygame.draw.rect(self.screen, RED, (enemy['x'] * TILE_SIZE + self.camera_x,
                                                enemy['y'] * TILE_SIZE + self.camera_y,
                                                TILE_SIZE, TILE_SIZE))
            text_surf = self.font.render("E", True, WHITE)
            self.screen.blit(text_surf, (enemy['x'] * TILE_SIZE + self.camera_x + TILE_SIZE // 4,
                                         enemy['y'] * TILE_SIZE + self.camera_y + TILE_SIZE // 4))

        # Draw merchants
        for merchant in self.level_data['merchants']: # New: Draw merchants
            pygame.draw.rect(self.screen, PURPLE, (merchant['x'] * TILE_SIZE + self.camera_x,
                                                   merchant['y'] * TILE_SIZE + self.camera_y,
                                                   TILE_SIZE, TILE_SIZE))
            text_surf = self.font.render("M", True, WHITE)
            self.screen.blit(text_surf, (merchant['x'] * TILE_SIZE + self.camera_x + TILE_SIZE // 4,
                                         merchant['y'] * TILE_SIZE + self.camera_y + TILE_SIZE // 4))

        # Draw doors
        for door in self.level_data['doors']: # New: Draw doors
            pygame.draw.rect(self.screen, DARK_BROWN, (door['x'] * TILE_SIZE + self.camera_x,
                                                 door['y'] * TILE_SIZE + self.camera_y,
                                                 TILE_SIZE, TILE_SIZE))
            text_surf = self.font.render("D", True, WHITE)
            self.screen.blit(text_surf, (door['x'] * TILE_SIZE + self.camera_x + TILE_SIZE // 4,
                                         door['y'] * TILE_SIZE + self.camera_y + TILE_SIZE // 4))

        # Draw player spawn
        player_spawn = self.level_data['player_spawn']
        pygame.draw.rect(self.screen, GREEN, (player_spawn['x'] * TILE_SIZE + self.camera_x,
                                              player_spawn['y'] * TILE_SIZE + self.camera_y,
                                              TILE_SIZE, TILE_SIZE))
        text_surf = self.font.render("S", True, WHITE)
        self.screen.blit(text_surf, (player_spawn['x'] * TILE_SIZE + self.camera_x + TILE_SIZE // 4,
                                     player_spawn['y'] * TILE_SIZE + self.camera_y + TILE_SIZE // 4))

        # Draw current tool indicator
        mouse_x, mouse_y = pygame.mouse.get_pos()
        current_tile_x = (mouse_x - self.camera_x) // TILE_SIZE * TILE_SIZE + self.camera_x
        current_tile_y = (mouse_y - self.camera_y) // TILE_SIZE * TILE_SIZE + self.camera_y

        if self.selected_tool == 'wall':
            pygame.draw.rect(self.screen, CYAN, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
        elif self.selected_tool == 'pot':
            pygame.draw.rect(self.screen, BROWN, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
        elif self.selected_tool == 'enemy':
            pygame.draw.rect(self.screen, RED, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
        elif self.selected_tool == 'player':
            pygame.draw.rect(self.screen, GREEN, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
        elif self.selected_tool == 'merchant': # New: Tool indicator for merchant
            pygame.draw.rect(self.screen, PURPLE, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
        elif self.selected_tool == 'door': # New: Tool indicator for door
            pygame.draw.rect(self.screen, DARK_BROWN, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
        elif self.selected_tool == 'erase':
            pygame.draw.rect(self.screen, YELLOW, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)


        # Draw UI text
        tool_text = self.font.render(f"Tool: {self.selected_tool.capitalize()}", True, WHITE)
        self.screen.blit(tool_text, (10, 10))
        instructions_text = self.font.render("1: Wall, 2: Pot, 3: Enemy, 4: Player, 5: Merchant, 6: Door, E: Erase, S: Save, Arrows: Scroll, Left/Right Click: Place/Erase", True, WHITE)
        self.screen.blit(instructions_text, (10, 30))

        pygame.display.flip()

    def run(self):
        while self.running:
            self.clock.tick(EDITOR_FPS)
            self.handle_input()
            self.draw()
        pygame.quit()

if __name__ == '__main__':
    editor = LevelEditor()
    editor.run()