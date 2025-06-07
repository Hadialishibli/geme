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
PURPLE = (128, 0, 128) # For keys
ORANGE = (255, 165, 0) # For doors
DARK_BLUE = (0, 0, 100) # For menu background
LIGHT_BLUE = (100, 100, 255) # For menu highlight

# --- Helper Functions ---
def load_level_data(filename):
    """Loads level data from a JSON file."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            # Ensure new lists exist, or initialize them if not present
            data.setdefault("merchants", [])
            data.setdefault("doors", [])
            data.setdefault("keys", [])
            return data
    except FileNotFoundError:
        print(f"Warning: Level file '{filename}' not found. Creating a new one.")
        return {
            "map_width": 30,
            "map_height": 20,
            "player_spawn": {"x": 1, "y": 1},
            "walls": [],
            "pots": [],
            "enemies": [],
            "merchants": [], # New: Initialize merchants list
            "doors": [],     # New: Initialize doors list
            "keys": []       # New: Initialize keys list
        }
    except json.JSONDecodeError:
        print(f"Error: Could not parse '{filename}'. Check for syntax errors. Creating a new one.")
        return {
            "map_width": 30,
            "map_height": 20,
            "player_spawn": {"x": 1, "y": 1},
            "walls": [],
            "pots": [],
            "enemies": [],
            "merchants": [], # New: Initialize merchants list
            "doors": [],     # New: Initialize doors list
            "keys": []       # New: Initialize keys list
        }

def save_level_data(filename, data):
    """Saves level data to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Level data saved to '{filename}'.")

# --- Editor Class ---
class LevelEditor:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Level Editor")
        self.clock = pygame.time.Clock()
        self.running = True

        self.font = pygame.font.Font(None, 30)

        self.level_data = load_level_data("level.json")
        self.map_width_pixels = self.level_data['map_width'] * TILE_SIZE
        self.map_height_pixels = self.level_data['map_height'] * TILE_SIZE

        self.camera_x = 0
        self.camera_y = 0

        self.tools = ['wall', 'pot', 'enemy', 'player', 'merchant', 'door', 'key', 'erase'] # MODIFIED: Added 'key'
        self.selected_tool_index = 0
        self.selected_tool = self.tools[self.selected_tool_index]

        self.menu_open = False # New: State for menu
        self.menu_items = ['wall', 'pot', 'enemy', 'player', 'merchant', 'door', 'key', 'erase'] # MODIFIED: Added 'key'
        self.menu_selection_index = 0

    def handle_input(self):
        """Handles user input for editor controls."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # New: Menu handling
                if event.key == pygame.K_e:
                    self.menu_open = not self.menu_open # Toggle menu
                    self.menu_selection_index = self.tools.index(self.selected_tool) if self.selected_tool in self.tools else 0 # Reset menu selection to current tool

                if self.menu_open:
                    if event.key == pygame.K_UP:
                        self.menu_selection_index = (self.menu_selection_index - 1) % len(self.menu_items)
                    elif event.key == pygame.K_DOWN:
                        self.menu_selection_index = (self.menu_selection_index + 1) % len(self.menu_items)
                    elif event.key == pygame.K_RETURN: # Enter key to select
                        self.selected_tool = self.menu_items[self.menu_selection_index]
                        self.menu_open = False # Close menu after selection
                else:
                    # Camera scrolling with arrow keys
                    if event.key == pygame.K_LEFT:
                        self.camera_x += TILE_SIZE * 5 # Scroll faster
                    if event.key == pygame.K_RIGHT:
                        self.camera_x -= TILE_SIZE * 5
                    if event.key == pygame.K_UP:
                        self.camera_y += TILE_SIZE * 5
                    if event.key == pygame.K_DOWN:
                        self.camera_y -= TILE_SIZE * 5
                    
                    # Clamp camera to map boundaries
                    self.camera_x = max(min(0, self.camera_x), -(self.map_width_pixels - SCREEN_WIDTH))
                    self.camera_y = max(min(0, self.map_height_pixels - SCREEN_HEIGHT), self.camera_y) # Fix clamp
                    self.camera_x = max(min(0, self.camera_x), -(self.map_width_pixels - SCREEN_WIDTH))
                    self.camera_y = max(min(0, self.camera_y), -(self.map_height_pixels - SCREEN_HEIGHT))

                    # Save functionality
                    if event.key == pygame.K_s:
                        save_level_data("level.json", self.level_data)
            
            if not self.menu_open and event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                world_x = (mouse_x - self.camera_x) // TILE_SIZE
                world_y = (mouse_y - self.camera_y) // TILE_SIZE

                if event.button == 1: # Left click to place/select
                    self.place_at_position(world_x, world_y)
                elif event.button == 3: # Right click to erase
                    self.erase_at_position(world_x, world_y)

    def place_at_position(self, x, y):
        """Places an object at the given tile coordinates based on the selected tool."""
        if not (0 <= x < self.level_data['map_width'] and 0 <= y < self.level_data['map_height']):
            print("Cannot place outside map boundaries.")
            return

        # Erase existing objects at this position before placing, if it's not 'erase' tool
        if self.selected_tool != 'erase':
            self.erase_at_position(x, y, True) # Erase existing if any before placing new

        if self.selected_tool == 'wall':
            # Check if a wall already exists at this exact single tile position
            # This editor places 1x1 walls, so check for intersection with existing walls
            new_wall = {"x": x, "y": y, "w": 1, "h": 1}
            # Simple check for existing 1x1 wall at same spot
            if not any(w['x'] == x and w['y'] == y and w['w'] == 1 and w['h'] == 1 for w in self.level_data['walls']):
                self.level_data['walls'].append(new_wall)
        elif self.selected_tool == 'pot':
            if not any(p['x'] == x and p['y'] == y for p in self.level_data['pots']):
                self.level_data['pots'].append({"x": x, "y": y})
        elif self.selected_tool == 'enemy':
            if not any(e['x'] == x and e['y'] == y for e in self.level_data['enemies']):
                self.level_data['enemies'].append({"type": "melee", "x": x, "y": y})
        elif self.selected_tool == 'player':
            # Remove previous player spawn and set new one
            self.level_data['player_spawn'] = {"x": x, "y": y}
        elif self.selected_tool == 'merchant': # New: Place merchant
            if not any(m['x'] == x and m['y'] == y for m in self.level_data['merchants']):
                self.level_data['merchants'].append({"x": x, "y": y})
        elif self.selected_tool == 'door': # New: Place door
            if not any(d['x'] == x and d['y'] == y for d in self.level_data['doors']):
                self.level_data['doors'].append({"x": x, "y": y})
        elif self.selected_tool == 'key': # MODIFIED: Place key
            if not any(k['x'] == x and k['y'] == y for k in self.level_data['keys']):
                self.level_data['keys'].append({"x": x, "y": y})
        elif self.selected_tool == 'erase':
            self.erase_at_position(x, y) # Call erase directly if 'erase' is selected

    def erase_at_position(self, x, y, check_only=False):
        """Erases an object at the given tile coordinates."""
        erased = False

        # Erase wall
        self.level_data['walls'] = [
            w for w in self.level_data['walls']
            if not (w['x'] <= x < w['x'] + w['w'] and w['y'] <= y < w['y'] + w['h'])
        ]
        # Erase pot
        self.level_data['pots'] = [p for p in self.level_data['pots'] if not (p['x'] == x and p['y'] == y)]
        # Erase enemy
        self.level_data['enemies'] = [e for e in self.level_data['enemies'] if not (e['x'] == x and e['y'] == y)]
        # Erase merchant
        self.level_data['merchants'] = [m for m in self.level_data['merchants'] if not (m['x'] == x and m['y'] == y)]
        # Erase door
        self.level_data['doors'] = [d for d in self.level_data['doors'] if not (d['x'] == x and d['y'] == y)]
        # MODIFIED: Erase key
        self.level_data['keys'] = [k for k in self.level_data['keys'] if not (k['x'] == x and k['y'] == y)]


        # Player spawn is a single point, so it's not 'erased' but rather moved when a new one is placed
        # or can be set to a default if you want an explicit erase for player spawn.
        # For now, placing a new player spawn automatically overwrites the old one.

        # If check_only is True, we just modified the list to remove, but don't print "Erased"
        if not check_only:
            print(f"Erased content at ({x}, {y})")


    def draw_grid(self):
        """Draws the grid lines for the editor."""
        for x in range(self.level_data['map_width']):
            pygame.draw.line(self.screen, DARK_BLUE, 
                             (x * TILE_SIZE + self.camera_x, self.camera_y), 
                             (x * TILE_SIZE + self.camera_x, self.map_height_pixels + self.camera_y))
        for y in range(self.level_data['map_height']):
            pygame.draw.line(self.screen, DARK_BLUE, 
                             (self.camera_x, y * TILE_SIZE + self.camera_y), 
                             (self.map_width_pixels + self.camera_x, y * TILE_SIZE + self.camera_y))

    def draw_menu(self):
        """New: Draws the tool selection menu."""
        menu_width = 200
        menu_item_height = 30
        menu_start_x = SCREEN_WIDTH - menu_width - 10
        menu_start_y = 10

        pygame.draw.rect(self.screen, DARK_BLUE, (menu_start_x, menu_start_y, menu_width, len(self.menu_items) * menu_item_height + 10))
        
        for i, item in enumerate(self.menu_items):
            item_rect = pygame.Rect(menu_start_x + 5, menu_start_y + 5 + i * menu_item_height, menu_width - 10, menu_item_height)
            
            if i == self.menu_selection_index:
                pygame.draw.rect(self.screen, LIGHT_BLUE, item_rect) # Highlight selected item

            item_text = self.font.render(item.capitalize(), True, WHITE)
            self.screen.blit(item_text, item_rect.topleft)

    def draw(self):
        """Draws all elements on the editor screen."""
        self.screen.fill(BLACK)
        
        # Draw background tiles (optional, for visual clarity)
        for x in range(self.level_data['map_width']):
            for y in range(self.level_data['map_height']):
                tile_rect = pygame.Rect(x * TILE_SIZE + self.camera_x, y * TILE_SIZE + self.camera_y, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(self.screen, (30, 30, 30), tile_rect, 1) # Light grey border

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
        # Draw enemies
        for enemy in self.level_data['enemies']:
            pygame.draw.rect(self.screen, RED, (enemy['x'] * TILE_SIZE + self.camera_x,
                                                enemy['y'] * TILE_SIZE + self.camera_y,
                                                TILE_SIZE, TILE_SIZE))
        # Draw player spawn
        player_spawn = self.level_data['player_spawn']
        pygame.draw.rect(self.screen, GREEN, (player_spawn['x'] * TILE_SIZE + self.camera_x,
                                              player_spawn['y'] * TILE_SIZE + self.camera_y,
                                              TILE_SIZE, TILE_SIZE))
        
        # New: Draw merchants
        for merchant in self.level_data['merchants']:
            pygame.draw.rect(self.screen, BLUE, (merchant['x'] * TILE_SIZE + self.camera_x,
                                                 merchant['y'] * TILE_SIZE + self.camera_y,
                                                 TILE_SIZE, TILE_SIZE))

        # New: Draw doors
        for door in self.level_data['doors']:
            pygame.draw.rect(self.screen, ORANGE, (door['x'] * TILE_SIZE + self.camera_x,
                                                  door['y'] * TILE_SIZE + self.camera_y,
                                                  TILE_SIZE, TILE_SIZE))

        # MODIFIED: Draw keys
        for key in self.level_data['keys']:
            pygame.draw.rect(self.screen, PURPLE, (key['x'] * TILE_SIZE + self.camera_x,
                                                  key['y'] * TILE_SIZE + self.camera_y,
                                                  TILE_SIZE, TILE_SIZE))

        self.draw_grid()

        # Draw highlight for current mouse position (only if menu is not open)
        if not self.menu_open:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            current_tile_x = (mouse_x - self.camera_x) // TILE_SIZE * TILE_SIZE + self.camera_x
            current_tile_y = (mouse_y - self.camera_y) // TILE_SIZE * TILE_SIZE + self.camera_y

            if 0 <= (mouse_x - self.camera_x) // TILE_SIZE < self.level_data['map_width'] and \
               0 <= (mouse_y - self.camera_y) // TILE_SIZE < self.level_data['map_height']:
                if self.selected_tool == 'wall':
                    pygame.draw.rect(self.screen, CYAN, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3) # Outline
                elif self.selected_tool == 'pot':
                    pygame.draw.rect(self.screen, BROWN, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
                elif self.selected_tool == 'enemy':
                    pygame.draw.rect(self.screen, RED, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
                elif self.selected_tool == 'player':
                    pygame.draw.rect(self.screen, GREEN, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
                elif self.selected_tool == 'merchant': # New: Draw merchant outline
                    pygame.draw.rect(self.screen, BLUE, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
                elif self.selected_tool == 'door': # New: Draw door outline
                    pygame.draw.rect(self.screen, ORANGE, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
                elif self.selected_tool == 'key': # MODIFIED: Draw key outline
                    pygame.draw.rect(self.screen, PURPLE, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)
                elif self.selected_tool == 'erase':
                    pygame.draw.rect(self.screen, YELLOW, (current_tile_x, current_tile_y, TILE_SIZE, TILE_SIZE), 3)


        # Draw UI text
        tool_text = self.font.render(f"Tool: {self.selected_tool.capitalize()}", True, WHITE)
        self.screen.blit(tool_text, (10, 10))
        # Updated instructions
        instructions_text = self.font.render("E: Open Menu, S: Save, Arrows: Scroll, Left Click: Place, Right Click: Erase", True, WHITE)
        self.screen.blit(instructions_text, (10, 40))

        if self.menu_open:
            self.draw_menu() # Draw menu if open

        pygame.display.flip()

    def run(self):
        """Runs the main editor loop."""
        while self.running:
            self.clock.tick(EDITOR_FPS)
            self.handle_input()
            self.draw()

# --- Main execution ---
if __name__ == '__main__':
    editor = LevelEditor()
    editor.run()
    pygame.quit()