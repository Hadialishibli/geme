import pygame
import json
import math

# --- Editor Settings ---
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
INITIAL_TILE_SIZE = 64
EDITOR_FPS = 60

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
GRID_COLOR = (40, 40, 40) # Darker grid lines

# --- Helper Functions ---
def load_level_data(filename):
    """Loads level data from a JSON file."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            # Ensure all object lists exist
            data.setdefault("player_spawn", {"x": 1, "y": 1})
            data.setdefault("walls", [])
            data.setdefault("pots", [])
            data.setdefault("enemies", [])
            data.setdefault("merchants", [])
            data.setdefault("doors", [])
            data.setdefault("keys", [])
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: Level file '{filename}' not found or invalid. Creating a new one.")
        return {
            "player_spawn": {"x": 1, "y": 1},
            "walls": [],
            "pots": [],
            "enemies": [],
            "merchants": [],
            "doors": [],
            "keys": []
        }

def save_level_data(filename, data):
    """Saves level data to a JSON file."""
    # Create a copy to avoid modifying the original dict while iterating
    data_to_save = data.copy()
    # Remove obsolete map size keys if they exist
    data_to_save.pop("map_width", None)
    data_to_save.pop("map_height", None)
    
    with open(filename, 'w') as f:
        json.dump(data_to_save, f, indent=4)
    print(f"Level data saved to '{filename}'.")

# --- Editor Class ---
class LevelEditor:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Infinite Level Editor")
        self.clock = pygame.time.Clock()
        self.running = True
        self.font = pygame.font.Font(None, 30)

        self.level_data = load_level_data("level.json")

        # Camera and Zoom
        self.camera_x = 0
        self.camera_y = 0
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.current_tile_size = INITIAL_TILE_SIZE * self.zoom_level

        # Tools
        self.tools = ['wall', 'pot', 'enemy', 'player', 'merchant', 'door', 'key', 'erase']
        self.selected_tool = self.tools[0]

        # Menu
        self.menu_open = False
        self.menu_items = self.tools
        self.menu_selection_index = 0

    def screen_to_world(self, sx, sy):
        """Converts screen coordinates to world coordinates, considering camera and zoom."""
        wx = (sx - self.camera_x) / self.zoom_level
        wy = (sy - self.camera_y) / self.zoom_level
        return wx, wy

    def world_to_screen(self, wx, wy):
        """Converts world coordinates to screen coordinates."""
        sx = wx * self.zoom_level + self.camera_x
        sy = wy * self.zoom_level + self.camera_y
        return sx, sy
        
    def get_tile_coords_from_mouse(self):
        """Gets the world grid coordinates (x, y) under the mouse cursor."""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_x, world_y = self.screen_to_world(mouse_x, mouse_y)
        tile_x = math.floor(world_x / INITIAL_TILE_SIZE)
        tile_y = math.floor(world_y / INITIAL_TILE_SIZE)
        return tile_x, tile_y

    def handle_input(self):
        """Handles user input for editor controls."""
        keys = pygame.key.get_pressed()
        
        # Pan the camera with arrow keys (if menu is closed)
        if not self.menu_open:
            scroll_speed = INITIAL_TILE_SIZE  # Move one tile at a time
            if keys[pygame.K_LEFT]:
                self.camera_x += scroll_speed
            if keys[pygame.K_RIGHT]:
                self.camera_x -= scroll_speed
            if keys[pygame.K_UP]:
                self.camera_y += scroll_speed
            if keys[pygame.K_DOWN]:
                self.camera_y -= scroll_speed

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # --- Keyboard Input ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # Toggle Menu
                if event.key == pygame.K_e:
                    self.menu_open = not self.menu_open
                    if self.menu_open:
                        self.menu_selection_index = self.tools.index(self.selected_tool)
                
                # Menu Navigation
                if self.menu_open:
                    if event.key == pygame.K_UP:
                        self.menu_selection_index = (self.menu_selection_index - 1) % len(self.menu_items)
                    elif event.key == pygame.K_DOWN:
                        self.menu_selection_index = (self.menu_selection_index + 1) % len(self.menu_items)
                    elif event.key == pygame.K_RETURN:
                        self.selected_tool = self.menu_items[self.menu_selection_index]
                        self.menu_open = False
                
                # Save
                elif event.key == pygame.K_s:
                    save_level_data("level.json", self.level_data)

            # --- Mouse Input ---
            if not self.menu_open:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    tile_x, tile_y = self.get_tile_coords_from_mouse()
                    
                    # Place / Erase
                    if event.button == 1: # Left click
                        self.place_at_position(tile_x, tile_y)
                    elif event.button == 3: # Right click
                        self.erase_at_position(tile_x, tile_y)
                    
                    # Zooming with scroll wheel
                    elif event.button == 4: # Scroll Up
                        self.zoom(1.1)
                    elif event.button == 5: # Scroll Down
                        self.zoom(0.9)

    def zoom(self, factor):
        """Zooms the camera, keeping the mouse position stable."""
        mouse_pos = pygame.mouse.get_pos()
        
        # Get world coordinates under mouse before zoom
        world_before_zoom_x, world_before_zoom_y = self.screen_to_world(*mouse_pos)
        
        # Apply zoom
        self.zoom_level *= factor
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, self.zoom_level))
        self.current_tile_size = INITIAL_TILE_SIZE * self.zoom_level

        # Get world coordinates under mouse after zoom
        world_after_zoom_x, world_after_zoom_y = self.screen_to_world(*mouse_pos)

        # Adjust camera to keep the world point under the mouse
        self.camera_x += (world_after_zoom_x - world_before_zoom_x) * self.zoom_level
        self.camera_y += (world_after_zoom_y - world_before_zoom_y) * self.zoom_level

    def place_at_position(self, x, y):
        """Places an object at the given tile coordinates."""
        self.erase_at_position(x, y, quiet=True) # Clear the tile first

        if self.selected_tool == 'wall':
            self.level_data['walls'].append({"x": x, "y": y, "w": 1, "h": 1})
        elif self.selected_tool == 'pot':
            self.level_data['pots'].append({"x": x, "y": y})
        elif self.selected_tool == 'enemy':
            self.level_data['enemies'].append({"type": "melee", "x": x, "y": y})
        elif self.selected_tool == 'player':
            self.level_data['player_spawn'] = {"x": x, "y": y}
        elif self.selected_tool == 'merchant':
            self.level_data['merchants'].append({"x": x, "y": y})
        elif self.selected_tool == 'door':
            self.level_data['doors'].append({"x": x, "y": y})
        elif self.selected_tool == 'key':
            self.level_data['keys'].append({"x": x, "y": y})
        elif self.selected_tool == 'erase':
            self.erase_at_position(x, y)

    def erase_at_position(self, x, y, quiet=False):
        """Erases any object at the given tile coordinates."""
        # A function to check if an object is at the given coordinates
        def at_coords(obj):
            return obj['x'] == x and obj['y'] == y

        # Filter out objects at the given coords from each list
        self.level_data['walls'] = [w for w in self.level_data['walls'] if not at_coords(w)]
        self.level_data['pots'] = [p for p in self.level_data['pots'] if not at_coords(p)]
        self.level_data['enemies'] = [e for e in self.level_data['enemies'] if not at_coords(e)]
        self.level_data['merchants'] = [m for m in self.level_data['merchants'] if not at_coords(m)]
        self.level_data['doors'] = [d for d in self.level_data['doors'] if not at_coords(d)]
        self.level_data['keys'] = [k for k in self.level_data['keys'] if not at_coords(k)]
        
        if not quiet:
            print(f"Erased content at ({x}, {y})")

    def draw_grid(self):
        """Draws a dynamic grid based on camera position and zoom."""
        # Calculate the visible portion of the world in tile coordinates
        start_world_x, start_world_y = self.screen_to_world(0, 0)
        end_world_x, end_world_y = self.screen_to_world(SCREEN_WIDTH, SCREEN_HEIGHT)

        start_tile_x = math.floor(start_world_x / INITIAL_TILE_SIZE)
        start_tile_y = math.floor(start_world_y / INITIAL_TILE_SIZE)
        end_tile_x = math.ceil(end_world_x / INITIAL_TILE_SIZE)
        end_tile_y = math.ceil(end_world_y / INITIAL_TILE_SIZE)

        # Draw vertical lines
        for x in range(start_tile_x, end_tile_x):
            sx1, sy1 = self.world_to_screen(x * INITIAL_TILE_SIZE, start_world_y)
            sx2, sy2 = self.world_to_screen(x * INITIAL_TILE_SIZE, end_world_y)
            pygame.draw.line(self.screen, GRID_COLOR, (sx1, sy1), (sx2, sy2))

        # Draw horizontal lines
        for y in range(start_tile_y, end_tile_y):
            sx1, sy1 = self.world_to_screen(start_world_x, y * INITIAL_TILE_SIZE)
            sx2, sy2 = self.world_to_screen(end_world_x, y * INITIAL_TILE_SIZE)
            pygame.draw.line(self.screen, GRID_COLOR, (sx1, sy1), (sx2, sy2))

    def draw_objects(self):
        """Draws all the objects from the level data."""
        ts = self.current_tile_size
        
        object_lists = {
            'walls': (GREY, self.level_data['walls']),
            'pots': (BROWN, self.level_data['pots']),
            'enemies': (RED, self.level_data['enemies']),
            'merchants': (BLUE, self.level_data['merchants']),
            'doors': (ORANGE, self.level_data['doors']),
            'keys': (PURPLE, self.level_data['keys']),
            'player': (GREEN, [self.level_data['player_spawn']])
        }

        for obj_type, (color, data_list) in object_lists.items():
            for obj in data_list:
                sx, sy = self.world_to_screen(obj['x'] * INITIAL_TILE_SIZE, obj['y'] * INITIAL_TILE_SIZE)
                # Cull objects that are off-screen
                if sx > SCREEN_WIDTH or sy > SCREEN_HEIGHT or sx + ts < 0 or sy + ts < 0:
                    continue
                
                rect = pygame.Rect(sx, sy, ts, ts)
                pygame.draw.rect(self.screen, color, rect)

    def draw_ui(self):
        """Draws the editor's user interface."""
        # Tool and instructions
        tool_text = self.font.render(f"Tool: {self.selected_tool.capitalize()} (E for menu)", True, WHITE)
        self.screen.blit(tool_text, (10, 10))
        instructions_text = self.font.render("S: Save, Arrows: Pan, Scroll: Zoom", True, WHITE)
        self.screen.blit(instructions_text, (10, 40))
        zoom_text = self.font.render(f"Zoom: {self.zoom_level:.2f}x", True, WHITE)
        self.screen.blit(zoom_text, (10, 70))

        # Draw menu if open
        if self.menu_open:
            menu_width = 200
            menu_item_height = 30
            menu_start_x = SCREEN_WIDTH - menu_width - 10
            menu_start_y = 10

            pygame.draw.rect(self.screen, DARK_BLUE, (menu_start_x, menu_start_y, menu_width, len(self.menu_items) * menu_item_height + 10))
            
            for i, item in enumerate(self.menu_items):
                item_rect = pygame.Rect(menu_start_x + 5, menu_start_y + 5 + i * menu_item_height, menu_width - 10, menu_item_height)
                
                if i == self.menu_selection_index:
                    pygame.draw.rect(self.screen, LIGHT_BLUE, item_rect)

                item_text = self.font.render(item.capitalize(), True, WHITE)
                self.screen.blit(item_text, (item_rect.x + 5, item_rect.y + 5))
                
    def draw_cursor_highlight(self):
        """Highlights the tile under the cursor."""
        if self.menu_open:
            return
            
        tile_x, tile_y = self.get_tile_coords_from_mouse()
        sx, sy = self.world_to_screen(tile_x * INITIAL_TILE_SIZE, tile_y * INITIAL_TILE_SIZE)
        rect = pygame.Rect(sx, sy, self.current_tile_size, self.current_tile_size)
        
        # Determine color based on tool
        color = CYAN if self.selected_tool != 'erase' else YELLOW
        pygame.draw.rect(self.screen, color, rect, 3) # Draw a thick border

    def draw(self):
        """Draws all elements on the editor screen."""
        self.screen.fill(BLACK)
        self.draw_grid()
        self.draw_objects()
        self.draw_cursor_highlight()
        self.draw_ui()
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

