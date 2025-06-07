import pygame
import json
import random
import math

# --- Game Settings and Constants ---
# This section holds all the major configuration values for the game.
# Editing these values will change the game's feel and behavior.

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TILE_SIZE = 64

# Player properties
PLAYER_HEALTH = 100
PLAYER_SPEED = 5
PLAYER_DAMAGE = 10
PLAYER_ATTACK_COOLDOWN = 400  # milliseconds
PLAYER_HIT_RECT = pygame.Rect(0, 0, 35, 35)

# Enemy properties
ENEMY_HEALTH = 50
ENEMY_DAMAGE = 10
ENEMY_SPEED = 2
ENEMY_KNOCKBACK = 20
ENEMY_AGGRO_RADIUS = 250 # Pixels

# Item properties
HEALTH_BOTTLE_HEAL_AMOUNT = 25

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
GREEN = (0, 150, 0)
BLUE = (0, 0, 255)
BROWN = (139, 69, 19)
GOLD = (255, 215, 0)
GREY = (128, 128, 128)
LIGHT_GREY = (200, 200, 200)
DARK_GREY = (50, 50, 50) # Added for screen overlays

# --- Helper Functions ---

def load_level(filename):
    """Loads level data from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Level file '{filename}' not found. Please create it.")
        pygame.quit()
        exit()
    except json.JSONDecodeError:
        print(f"Error: Could not parse '{filename}'. Check for syntax errors.")
        pygame.quit()
        exit()

# --- Game Object Classes ---

class Player(pygame.sprite.Sprite):
    """Represents the player character."""
    def __init__(self, game, x, y):
        super().__init__()
        self.game = game
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.hit_rect = PLAYER_HIT_RECT.copy()
        self.hit_rect.center = self.rect.center

        # Player stats and inventory
        self.health = PLAYER_HEALTH
        self.speed = PLAYER_SPEED
        self.damage = PLAYER_DAMAGE
        self.coins = 0
        self.arrows = 5
        self.health_bottles = 1

        # Movement and direction
        self.vx, self.vy = 0, 0
        self.direction = 'down'

        # Equipped item and attack state
        self.equipped_item = 'sword'  # 'sword' or 'bow'
        self.attacking = False
        self.last_attack_time = 0

    def get_input(self):
        """Handles player input for movement and actions."""
        self.vx, self.vy = 0, 0
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -self.speed
            self.direction = 'left'
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = self.speed
            self.direction = 'right'
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.vy = -self.speed
            self.direction = 'up'
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.vy = self.speed
            self.direction = 'down'
        
        # Diagonal movement correction
        if self.vx != 0 and self.vy != 0:
            self.vx *= 0.7071
            self.vy *= 0.7071

        # Action inputs
        if keys[pygame.K_SPACE]:
            self.attack()
        if keys[pygame.K_1]:
            self.equipped_item = 'sword'
            self.game.add_message("Equipped Sword.")
        if keys[pygame.K_2]:
            self.equipped_item = 'bow'
            self.game.add_message("Equipped Bow.")
        if keys[pygame.K_h]:
            self.use_health_bottle()

    def attack(self):
        """Performs an attack based on the equipped item."""
        now = pygame.time.get_ticks()
        if now - self.last_attack_time > PLAYER_ATTACK_COOLDOWN:
            self.last_attack_time = now
            self.attacking = True
            
            if self.equipped_item == 'sword':
                self.game.add_message("Swish!")
                # A sword attack creates a temporary hitbox
                attack_rect = self.get_attack_rect()
                for enemy in self.game.enemies:
                    if attack_rect.colliderect(enemy.hit_rect):
                        enemy.take_damage(self.damage)

            elif self.equipped_item == 'bow':
                if self.arrows > 0:
                    self.arrows -= 1
                    Projectile(self.game, self.rect.center, self.direction)
                    self.game.add_message("Thwip!")
                else:
                    self.game.add_message("Out of arrows!")

    def get_attack_rect(self):
        """Calculates the position of the sword attack hitbox."""
        attack_rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        if self.direction == 'up':
            attack_rect.midbottom = self.rect.midtop
        elif self.direction == 'down':
            attack_rect.midtop = self.rect.midbottom
        elif self.direction == 'left':
            attack_rect.midright = self.rect.midleft
        elif self.direction == 'right':
            attack_rect.midleft = self.rect.midright
        return attack_rect

    def use_health_bottle(self):
        """Consumes a health bottle to restore health."""
        if self.health_bottles > 0:
            if self.health < PLAYER_HEALTH:
                self.health_bottles -= 1
                self.health = min(PLAYER_HEALTH, self.health + HEALTH_BOTTLE_HEAL_AMOUNT)
                self.game.add_message(f"Healed for {HEALTH_BOTTLE_HEAL_AMOUNT} HP.")
            else:
                self.game.add_message("Health is already full.")
        else:
            self.game.add_message("No health bottles!")

    def move(self, dx, dy):
        """Moves the player and handles collisions."""
        if dx != 0:
            self.rect.x += dx
            self.hit_rect.centerx = self.rect.centerx
            self.collide_with_obstacles('x')
        if dy != 0:
            self.rect.y += dy
            self.hit_rect.centery = self.rect.centery
            self.collide_with_obstacles('y')

    def collide_with_obstacles(self, direction):
        """Checks for and resolves collisions with walls and pots."""
        hits = pygame.sprite.spritecollide(self, self.game.walls, False)
        hits += pygame.sprite.spritecollide(self, self.game.pots, False)
        
        if direction == 'x':
            if hits:
                if self.vx > 0: # Moving right
                    self.rect.right = hits[0].rect.left
                if self.vx < 0: # Moving left
                    self.rect.left = hits[0].rect.right
                self.vx = 0
                self.hit_rect.centerx = self.rect.centerx
        if direction == 'y':
            if hits:
                if self.vy > 0: # Moving down
                    self.rect.bottom = hits[0].rect.top
                if self.vy < 0: # Moving up
                    self.rect.top = hits[0].rect.bottom
                self.vy = 0
                self.hit_rect.centery = self.rect.centery
    
    def take_damage(self, amount):
        """Reduces player health."""
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.game.playing = False # Game over, transition to death screen

    def update(self):
        """Updates player state each frame."""
        self.get_input()
        self.move(self.vx, self.vy)
        
        # Reset attacking flag after a short duration
        if self.attacking and pygame.time.get_ticks() - self.last_attack_time > 100:
             self.attacking = False

class Enemy(pygame.sprite.Sprite):
    """Represents a melee enemy."""
    def __init__(self, game, x, y):
        super().__init__(game.all_sprites, game.enemies)
        self.game = game
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(RED)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.hit_rect = PLAYER_HIT_RECT.copy()
        self.hit_rect.center = self.rect.center

        self.health = ENEMY_HEALTH
        self.speed = ENEMY_SPEED

    def move_towards_player(self):
        """Calculates movement vector towards the player."""
        dx, dy = self.game.player.rect.centerx - self.rect.centerx, self.game.player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            dx, dy = dx / dist, dy / dist  # Normalize
        self.vx, self.vy = dx * self.speed, dy * self.speed
        
        self.rect.x += self.vx
        self.collide_with_walls('x')
        self.rect.y += self.vy
        self.collide_with_walls('y')
        
        self.hit_rect.center = self.rect.center


    def collide_with_walls(self, direction):
        """Enemy collision with walls"""
        hits = pygame.sprite.spritecollide(self, self.game.walls, False)
        if hits:
            if direction == 'x':
                if self.vx > 0: self.rect.right = hits[0].rect.left
                if self.vx < 0: self.rect.left = hits[0].rect.right
                self.vx = 0
            if direction == 'y':
                if self.vy > 0: self.rect.bottom = hits[0].rect.top
                if self.vy < 0: self.rect.top = hits[0].rect.bottom
                self.vy = 0

    def take_damage(self, amount):
        """Reduces enemy health and handles death."""
        self.health -= amount
        if self.health <= 0:
            self.kill() # Remove from all sprite groups

    def update(self):
        """Updates enemy state each frame."""
        # Check distance to player
        player_dist = math.hypot(self.game.player.rect.centerx - self.rect.centerx,
                                 self.game.player.rect.centery - self.rect.centery)

        if player_dist < ENEMY_AGGRO_RADIUS:
            self.move_towards_player()
        
        # Check for collision with player to deal damage
        if self.hit_rect.colliderect(self.game.player.hit_rect):
            self.game.player.take_damage(ENEMY_DAMAGE)

class Wall(pygame.sprite.Sprite):
    """Represents an impassable wall."""
    def __init__(self, game, x, y, w, h):
        super().__init__(game.all_sprites, game.walls)
        self.game = game
        self.rect = pygame.Rect(x, y, w, h)
        self.image = pygame.Surface((w, h))
        self.image.fill(GREY)

class Pot(pygame.sprite.Sprite):
    """Represents a destructible pot that drops loot."""
    def __init__(self, game, x, y):
        super().__init__(game.all_sprites, game.pots)
        self.game = game
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(BROWN)
        self.rect = self.image.get_rect(topleft=(x, y))

    def destroy(self):
        """Handles pot destruction and loot drops."""
        loot_options = ['arrows', 'coin', 'health_bottle']
        weights = [0.6, 0.3, 0.1] # 60% arrows, 30% coin, 10% bottle
        chosen_loot = random.choices(loot_options, weights, k=1)[0]

        Item(self.game, self.rect.center, chosen_loot)
        self.game.add_message(f"Pot dropped {chosen_loot.replace('_', ' ')}!")
        self.kill()

class Projectile(pygame.sprite.Sprite):
    """Represents an arrow shot by the player."""
    def __init__(self, game, pos, direction):
        super().__init__(game.all_sprites, game.projectiles)
        self.game = game
        self.image = pygame.Surface((10, 10))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect(center=pos)
        self.speed = 10
        
        if direction == 'up':
            self.vy = -self.speed
            self.vx = 0
        elif direction == 'down':
            self.vy = self.speed
            self.vx = 0
        elif direction == 'left':
            self.vx = -self.speed
            self.vy = 0
        elif direction == 'right':
            self.vx = self.speed
            self.vy = 0
            
    def update(self):
        """Moves the projectile and checks for collisions."""
        self.rect.x += self.vx
        self.rect.y += self.vy
        
        # Kill if it goes off-screen
        if not self.game.camera.get_rect().colliderect(self.rect):
            self.kill()
        
        # Check for collisions with enemies
        hits = pygame.sprite.spritecollide(self, self.game.enemies, False)
        if hits:
            for enemy in hits:
                enemy.take_damage(self.game.player.damage)
            self.kill()
            
        # Check for collisions with pots
        # Note: spritecollide with dokill=True will remove the pot from its groups automatically.
        # However, the Pot.destroy() method contains the loot drop logic.
        # A more robust solution would be to call pot.destroy() on collision.
        # For simplicity here, we'll iterate and check.
        collided_pots = pygame.sprite.spritecollide(self, self.game.pots, False)
        for pot in collided_pots:
            pot.destroy() # Call the destroy method to handle loot
            self.kill() # Kill the projectile after hitting a pot

class Item(pygame.sprite.Sprite):
    """Represents a collectible item on the ground."""
    def __init__(self, game, pos, item_type):
        super().__init__(game.all_sprites, game.items)
        self.game = game
        self.type = item_type
        self.image = pygame.Surface((TILE_SIZE // 2, TILE_SIZE // 2))
        
        if self.type == 'health_bottle':
            self.image.fill(RED)
        elif self.type == 'coin':
            self.image.fill(GOLD)
        elif self.type == 'arrows':
            self.image.fill(WHITE)
            
        self.rect = self.image.get_rect(center=pos)

class Camera:
    """Manages the game's viewport."""
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        """Applies the camera offset to a sprite's rect."""
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        """Applies the camera offset to a rect."""
        return rect.move(self.camera.topleft)

    def update(self, target):
        """Updates the camera's position to follow the target."""
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)
        
        # Limit scrolling to the map size
        x = min(0, x) # left
        y = min(0, y) # top
        x = max(-(self.width - SCREEN_WIDTH), x) # right
        y = max(-(self.height - SCREEN_HEIGHT), y) # bottom
        
        self.camera = pygame.Rect(x, y, self.width, self.height)

    def get_rect(self):
        """Returns a rect representing the visible area of the world."""
        return pygame.Rect(-self.camera.x, -self.camera.y, SCREEN_WIDTH, SCREEN_HEIGHT)

class UI:
    """Handles drawing all UI elements."""
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.Font(None, 30)
        self.large_font = pygame.font.Font(None, 75) # For titles
        self.button_font = pygame.font.Font(None, 40) # For buttons
        self.message_font = pygame.font.Font(None, 24)
        self.messages = []

    def add_message(self, text):
        self.messages.append({'text': text, 'time': pygame.time.get_ticks()})
        # Keep only the last 5 messages
        if len(self.messages) > 5:
            self.messages.pop(0)

    def draw_player_stats(self, surface):
        # Health bar
        health_ratio = self.game.player.health / PLAYER_HEALTH
        bar_width = 150
        bar_height = 20
        fill_width = int(bar_width * health_ratio)
        health_bar_rect = pygame.Rect(10, 10, bar_width, bar_height)
        fill_rect = pygame.Rect(10, 10, fill_width, bar_height)
        pygame.draw.rect(surface, RED, health_bar_rect)
        pygame.draw.rect(surface, GREEN, fill_rect)
        
        # Stats text
        stats_text = self.font.render(
            f"Coins: {self.game.player.coins} | Arrows: {self.game.player.arrows} | Potions: {self.game.player.health_bottles}",
            True, WHITE
        )
        surface.blit(stats_text, (10, 40))

        # Equipped item text
        equipped_text = self.font.render(
            f"Equipped (1,2): {self.game.player.equipped_item.title()}", True, WHITE
        )
        surface.blit(equipped_text, (SCREEN_WIDTH - equipped_text.get_width() - 10, 10))

    def draw_messages(self, surface):
        """Draws temporary messages to the screen."""
        now = pygame.time.get_ticks()
        for i, msg in enumerate(self.messages):
            if now - msg['time'] < 3000: # Display for 3 seconds
                msg_surface = self.message_font.render(msg['text'], True, WHITE)
                y_pos = SCREEN_HEIGHT - (len(self.messages) - i) * 25 - 10
                surface.blit(msg_surface, (10, y_pos))

    def draw_text_center(self, surface, text, font, color, y_offset=0):
        """Helper to draw text centered on screen."""
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + y_offset))
        surface.blit(text_surface, text_rect)

    def draw_button(self, surface, text, rect, color, hover_color):
        """Helper to draw a button and return if hovered/clicked."""
        mouse_pos = pygame.mouse.get_pos()
        clicked = False

        if rect.collidepoint(mouse_pos):
            pygame.draw.rect(surface, hover_color, rect)
            if pygame.mouse.get_pressed()[0]:
                clicked = True
        else:
            pygame.draw.rect(surface, color, rect)
        
        text_surface = self.button_font.render(text, True, WHITE)
        text_rect = text_surface.get_rect(center=rect.center)
        surface.blit(text_surface, text_rect)
        return clicked


    def draw(self, surface):
        self.draw_player_stats(surface)
        self.draw_messages(surface)
        
# --- Main Game Class ---

class Game:
    """The main class that runs the game."""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Top-Down Adventure")
        self.clock = pygame.time.Clock()
        self.running = True
        self.playing = False # True when actively playing the game
        self.paused = False  # True when game is paused
        self.game_over = False # True when player health is 0

        self.level_data = None
        self.ui = UI(self)

    def new(self):
        """Initializes a new game."""
        # Sprite groups
        self.all_sprites = pygame.sprite.Group()
        self.walls = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.pots = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.items = pygame.sprite.Group()

        # Load level data from JSON
        self.level_data = load_level("level.json")
        
        # Determine map size
        map_width = self.level_data['map_width'] * TILE_SIZE
        map_height = self.level_data['map_height'] * TILE_SIZE
        self.camera = Camera(map_width, map_height)

        # Create game objects based on level data
        player_spawn = self.level_data['player_spawn']
        self.player = Player(self, player_spawn['x'] * TILE_SIZE, player_spawn['y'] * TILE_SIZE)
        self.all_sprites.add(self.player)

        for wall in self.level_data.get('walls', []):
            Wall(self, wall['x'] * TILE_SIZE, wall['y'] * TILE_SIZE, wall['w'] * TILE_SIZE, wall['h'] * TILE_SIZE)

        for pot in self.level_data.get('pots', []):
            Pot(self, pot['x'] * TILE_SIZE, pot['y'] * TILE_SIZE)

        for enemy in self.level_data.get('enemies', []):
            if enemy['type'] == 'melee':
                Enemy(self, enemy['x'] * TILE_SIZE, enemy['y'] * TILE_SIZE)

        self.playing = True
        self.paused = False # Reset pause state on new game
        self.game_over = False # Reset game over state on new game
        self.run()

    def run(self):
        """The main game loop."""
        while self.playing:
            self.dt = self.clock.tick(60) / 1000 # Delta time in seconds
            self.events()
            if not self.paused and not self.game_over: # Only update if not paused and not game over
                self.update()
            self.draw()
            
            if self.paused: # Display pause screen if paused
                self.show_pause_screen()
            elif self.game_over: # Display death screen if game over
                self.show_death_screen()
            
            pygame.display.flip() # Only one flip at the end of the frame

    def events(self):
        """Handles all game events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.playing = False
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.playing and not self.game_over: # Only toggle pause if game is actively playing and not game over
                        self.paused = not self.paused # Toggle pause state
                        if self.paused: # Clear messages when pausing to avoid clutter
                            self.ui.messages.clear() 

    def update(self):
        """Updates all game objects."""
        self.all_sprites.update()
        self.camera.update(self.player)

        # Check for player picking up items
        item_hits = pygame.sprite.spritecollide(self.player, self.items, True)
        for item in item_hits:
            if item.type == 'health_bottle':
                self.player.health_bottles += 1
                self.add_message("Picked up a health bottle.")
            if item.type == 'coin':
                self.player.coins += 1
                self.add_message("Picked up a coin.")
            if item.type == 'arrows':
                self.player.arrows += 5
                self.add_message("Picked up 5 arrows.")

        # Sword attacks on pots
        if self.player.attacking and self.player.equipped_item == 'sword':
            attack_rect = self.player.get_attack_rect()
            for pot in self.pots:
                if attack_rect.colliderect(pot.rect):
                    pot.destroy()
        
        # Check if player died
        if self.player.health <= 0 and not self.game_over:
            self.game_over = True
            self.playing = False # Stop the main game loop updates
            self.add_message("You have fallen!") # Inform the player


    def draw(self):
        """Draws everything to the screen."""
        self.screen.fill(BLACK) # Background color

        # Draw all sprites offset by the camera
        for sprite in self.all_sprites:
            self.screen.blit(sprite.image, self.camera.apply(sprite))
            
        # Draw player attack animation (a simple flash)
        if self.player.attacking and self.player.equipped_item == 'sword':
            attack_rect = self.player.get_attack_rect()
            # We need to create a temporary surface to draw the semi-transparent rect
            s = pygame.Surface((attack_rect.width, attack_rect.height), pygame.SRCALPHA)
            s.fill((255, 255, 0, 128))  # Yellow, 50% transparent
            self.screen.blit(s, self.camera.apply_rect(attack_rect)) # Corrected method call


        # Draw UI on top of everything
        self.ui.draw(self.screen)
        
        # Removed pygame.display.flip() from here, moved to run()
        
    def add_message(self, text):
        """Convenience method to add a message to the UI."""
        self.ui.add_message(text)

    def show_start_screen(self):
        """Displays the start screen."""
        # For now, directly starts a new game. You can expand this later.
        self.new()

    def show_pause_screen(self):
        """Displays the pause screen."""
        pause_screen_running = True
        self.ui.messages.clear() # Clear any existing messages
        self.add_message("Game Paused")

        while pause_screen_running:
            # Dim the background
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150)) # Black with 150 alpha (semi-transparent)
            self.screen.blit(s, (0, 0))

            self.ui.draw_text_center(self.screen, "PAUSED", self.ui.large_font, WHITE, -100)

            # Exit Button
            exit_button_rect = pygame.Rect(
                SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT / 2 + 50, 200, 50
            )

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.playing = False
                    pause_screen_running = False
                    self.paused = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pause_screen_running = False
                        self.paused = False # Unpause the game
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if exit_button_rect.collidepoint(event.pos):
                        self.running = False
                        self.playing = False
                        pause_screen_running = False
                        self.paused = False

            if self.ui.draw_button(self.screen, "Exit Game", exit_button_rect, DARK_GREY, GREY):
                self.running = False
                self.playing = False
                pause_screen_running = False
                self.paused = False

            pygame.display.flip()

    def show_death_screen(self):
        """Displays the game over/death screen."""
        death_screen_running = True
        
        while death_screen_running:
            # Dim the background
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180)) # Darker black for death screen
            self.screen.blit(s, (0, 0))

            self.ui.draw_text_center(self.screen, "GAME OVER", self.ui.large_font, RED, -100)

            # Respawn Button
            respawn_button_rect = pygame.Rect(
                SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT / 2 + 20, 200, 50
            )

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    death_screen_running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if respawn_button_rect.collidepoint(event.pos):
                        death_screen_running = False
                        self.new() # Restart the game
                        
            if self.ui.draw_button(self.screen, "Respawn", respawn_button_rect, DARK_GREY, RED):
                death_screen_running = False
                self.new() # Restart the game

            pygame.display.flip()

# --- Main execution ---
if __name__ == '__main__':
    g = Game()
    g.show_start_screen()
    while g.running:
        # The show_go_screen() was intended for a simple game over.
        # Now, the death screen logic is handled by show_death_screen().
        # This line is no longer needed as g.playing will be False and
        # g.run() will call show_death_screen directly.
        # You can remove or comment out the following line if you wish.
        # g.show_go_screen() 
        pass # Keep the while loop running to allow restarting the game via respawn button
    pygame.quit()