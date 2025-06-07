import pygame
import json
import random
import math

# --- Game Settings and Constants ---
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
MERCHANT_ARROW_COST = 3
MERCHANT_ARROW_AMOUNT = 5
MERCHANT_POTION_COST = 5
MERCHANT_POTION_AMOUNT = 1

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
PURPLE = (128, 0, 128) # For merchant
YELLOW = (255, 255, 0) # For key
DARK_BROWN = (101, 67, 33) # For door

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
        self.keys = 0 # New: Keys for doors

        # Movement and direction
        self.vx, self.vy = 0, 0
        self.direction = 'down'

        # Equipped item and attack state
        self.equipped_item = 'sword'  # 'sword' or 'bow'
        self.attacking = False
        self.last_attack_time = 0

        # Interaction state
        self.can_interact = False
        self.interact_target = None
        self.dialogue_active = False # New: For merchant dialogue

    def get_input(self):
        """Handles player input for movement and actions."""
        self.vx, self.vy = 0, 0
        keys = pygame.key.get_pressed()

        if not self.dialogue_active: # Player cannot move or attack during dialogue
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
            
            # Interaction key
            if keys[pygame.K_e] and self.can_interact:
                if self.interact_target:
                    self.interact_target.interact(self)
                self.can_interact = False # Prevent multiple interactions from one press
        else: # If dialogue is active, only process dialogue inputs
            pass # Dialogue input handled by UI

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
                # Check for pots on sword attack
                for pot in self.game.pots:
                    if attack_rect.colliderect(pot.rect):
                        pot.destroy()

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
        hits += pygame.sprite.spritecollide(self, self.game.doors, False) # New: Collide with doors
        
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
        
        # Check for proximity to interactive objects (merchant, doors)
        self.can_interact = False
        self.interact_target = None
        for merchant in self.game.merchants:
            if self.rect.colliderect(merchant.rect.inflate(TILE_SIZE, TILE_SIZE)): # Bigger interaction radius
                self.can_interact = True
                self.interact_target = merchant
                break # Only one interaction target at a time
        
        for door in self.game.doors:
            if self.rect.colliderect(door.rect.inflate(TILE_SIZE, TILE_SIZE)): # Bigger interaction radius
                self.can_interact = True
                self.interact_target = door
                break


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
        self.collide_with_obstacles('x')
        self.rect.y += self.vy
        self.collide_with_obstacles('y')
        
        self.hit_rect.center = self.rect.center

    def collide_with_obstacles(self, direction):
        """Enemy collision with walls, pots, doors, and other enemies."""
        hits = pygame.sprite.spritecollide(self, self.game.walls, False)
        hits += pygame.sprite.spritecollide(self, self.game.pots, False)
        hits += pygame.sprite.spritecollide(self, self.game.doors, False) # New: Collide with doors

        # Prevent enemies from overlapping other enemies
        other_enemies = self.game.enemies.copy()
        other_enemies.remove(self) # Remove self from the group
        hits += pygame.sprite.spritecollide(self, other_enemies, False)

        if direction == 'x':
            if hits:
                for hit in hits:
                    if self.vx > 0: self.rect.right = hit.rect.left
                    if self.vx < 0: self.rect.left = hit.rect.right
                    self.vx = 0
                self.hit_rect.centerx = self.rect.centerx
        if direction == 'y':
            if hits:
                for hit in hits:
                    if self.vy > 0: self.rect.bottom = hit.rect.top
                    if self.vy < 0: self.rect.top = hit.rect.bottom
                    self.vy = 0
                self.hit_rect.centery = self.rect.centery

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

        if player_dist < ENEMY_AGGRO_RADIUS and not self.game.player.dialogue_active: # Don't move if player in dialogue
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
        weights = [0.5, 0.3, 0.2]
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
        
        # MODIFIED: Kill if it goes too far off-screen, relative to camera view
        if not self.game.camera.get_rect().inflate(200, 200).colliderect(self.rect):
            self.kill()
        
        # Check for collisions with enemies
        hits = pygame.sprite.spritecollide(self, self.game.enemies, False)
        if hits:
            for enemy in hits:
                enemy.take_damage(self.game.player.damage)
            self.kill()
            
        # Check for collisions with pots
        collided_pots = pygame.sprite.spritecollide(self, self.game.pots, False)
        for pot in collided_pots:
            pot.destroy()
            self.kill()
        
        # Check for collisions with walls
        collided_walls = pygame.sprite.spritecollide(self, self.game.walls, False)
        if collided_walls:
            self.kill()

        # Check for collisions with doors
        collided_doors = pygame.sprite.spritecollide(self, self.game.doors, False)
        if collided_doors:
            self.kill() # Arrows bounce off doors

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
        elif self.type == 'key': # New: Key color
            self.image.fill(YELLOW)
            
        self.rect = self.image.get_rect(center=pos)

class Merchant(pygame.sprite.Sprite):
    """Represents a merchant character for buying items."""
    def __init__(self, game, x, y):
        super().__init__(game.all_sprites, game.merchants)
        self.game = game
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(PURPLE)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.dialogue_open = False
        self.last_interact_time = 0
        self.interaction_cooldown = 500 # milliseconds

    def interact(self, player):
        now = pygame.time.get_ticks()
        if now - self.last_interact_time > self.interaction_cooldown:
            self.last_interact_time = now
            self.dialogue_open = not self.dialogue_open # Toggle dialogue
            player.dialogue_active = self.dialogue_open # Set player's state
            if self.dialogue_open:
                self.game.add_message("Hello, traveler! What do you need?")
                self.game.ui.set_merchant_options(["Arrows (3 Coins)", "Potion (5 Coins)", "Exit"])
            else:
                self.game.add_message("Farewell!")
                self.game.ui.clear_merchant_options()

    def update(self):
        # Merchant doesn't move, but might have animation in future
        pass

class Door(pygame.sprite.Sprite):
    """Represents a door that requires a key to open."""
    def __init__(self, game, x, y):
        super().__init__(game.all_sprites, game.doors)
        self.game = game
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(DARK_BROWN)
        self.rect = self.image.get_rect(topleft=(x, y))

    def interact(self, player):
        now = pygame.time.get_ticks()
        if now - player.last_attack_time > 500: # Simple cooldown to prevent spamming
            player.last_attack_time = now # Reuse attack_time for interaction cooldown
            if player.keys > 0:
                player.keys -= 1
                self.game.add_message("The door creaks open!")
                self.kill() # Remove the door
            else:
                self.game.add_message("This door is locked. You need a key.")

class Camera:
    """Manages the game's viewport with infinite scrolling."""
    # MODIFIED: Removed map dimensions from constructor as they are no longer needed.
    def __init__(self):
        self.camera = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT) # Camera represents the viewport

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
        self.camera.topleft = (x, y)

    def get_rect(self):
        """Returns a rect representing the visible area of the world relative to world origin."""
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
        self.merchant_options = []
        self.selected_merchant_option = 0

    def add_message(self, text):
        self.messages.append({'text': text, 'time': pygame.time.get_ticks()})
        if len(self.messages) > 5:
            self.messages.pop(0)

    def set_merchant_options(self, options):
        self.merchant_options = options
        self.selected_merchant_option = 0

    def clear_merchant_options(self):
        self.merchant_options = []
        self.selected_merchant_option = 0

    def handle_merchant_input(self, event):
        if not self.game.player.dialogue_active or not self.merchant_options:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_merchant_option = (self.selected_merchant_option - 1) % len(self.merchant_options)
            elif event.key == pygame.K_DOWN:
                self.selected_merchant_option = (self.selected_merchant_option + 1) % len(self.merchant_options)
            elif event.key == pygame.K_RETURN:
                self.process_merchant_selection()

    def process_merchant_selection(self):
        if not self.merchant_options:
            return

        selection = self.merchant_options[self.selected_merchant_option]
        player = self.game.player

        if "Arrows" in selection:
            if player.coins >= MERCHANT_ARROW_COST:
                player.coins -= MERCHANT_ARROW_COST
                player.arrows += MERCHANT_ARROW_AMOUNT
                self.game.add_message(f"Bought {MERCHANT_ARROW_AMOUNT} arrows.")
            else:
                self.game.add_message("Not enough coins for arrows!")
        elif "Potion" in selection:
            if player.coins >= MERCHANT_POTION_COST:
                player.coins -= MERCHANT_POTION_COST
                player.health_bottles += MERCHANT_POTION_AMOUNT
                self.game.add_message(f"Bought {MERCHANT_POTION_AMOUNT} health potion.")
            else:
                self.game.add_message("Not enough coins for a potion!")
        elif "Exit" in selection:
            self.game.player.dialogue_active = False
            self.clear_merchant_options()
            self.game.add_message("See you again soon!")


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
            f"Coins: {self.game.player.coins} | Arrows: {self.game.player.arrows} | Potions: {self.game.player.health_bottles} | Keys: {self.game.player.keys}",
            True, WHITE
        )
        surface.blit(stats_text, (10, 40))

        # Equipped item text
        equipped_text = self.font.render(
            f"Equipped (1,2): {self.game.player.equipped_item.title()}", True, WHITE
        )
        surface.blit(equipped_text, (SCREEN_WIDTH - equipped_text.get_width() - 10, 10))

        # Interaction prompt
        if self.game.player.can_interact and not self.game.player.dialogue_active:
            interact_text = self.font.render("Press 'E' to Interact", True, YELLOW)
            text_rect = interact_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 50))
            surface.blit(interact_text, text_rect)


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

    def draw_merchant_dialogue(self, surface):
        if not self.game.player.dialogue_active or not self.merchant_options:
            return

        dialogue_rect = pygame.Rect(SCREEN_WIDTH / 4, SCREEN_HEIGHT / 4, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        pygame.draw.rect(surface, DARK_GREY, dialogue_rect)
        pygame.draw.rect(surface, WHITE, dialogue_rect, 3) # Border

        dialogue_prompt = self.font.render("What would you like?", True, WHITE)
        surface.blit(dialogue_prompt, (dialogue_rect.x + 20, dialogue_rect.y + 20))

        for i, option in enumerate(self.merchant_options):
            color = GOLD if i == self.selected_merchant_option else WHITE
            option_surf = self.font.render(option, True, color)
            surface.blit(option_surf, (dialogue_rect.x + 40, dialogue_rect.y + 70 + i * 40))


    def draw(self, surface):
        self.draw_player_stats(surface)
        self.draw_messages(surface)
        self.draw_merchant_dialogue(surface)
        
# --- Main Game Class ---

class Game:
    """The main class that runs the game."""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Top-Down Adventure")
        self.clock = pygame.time.Clock()
        self.running = True
        self.playing = False
        self.paused = False
        self.game_over = False

        self.level_data = None
        self.ui = UI(self)

    def new(self):
        """Initializes a new game."""
        self.all_sprites = pygame.sprite.Group()
        self.walls = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.pots = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.items = pygame.sprite.Group()
        self.merchants = pygame.sprite.Group()
        self.doors = pygame.sprite.Group()

        self.level_data = load_level("level.json")
        
        # MODIFIED: Initialize the infinite camera without map dimensions.
        self.camera = Camera()

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
        
        for merchant_data in self.level_data.get('merchants', []):
            Merchant(self, merchant_data['x'] * TILE_SIZE, merchant_data['y'] * TILE_SIZE)

        for door_data in self.level_data.get('doors', []):
            Door(self, door_data['x'] * TILE_SIZE, door_data['y'] * TILE_SIZE)

        for key_data in self.level_data.get('keys', []):
            item_x_pos = key_data['x'] * TILE_SIZE + (TILE_SIZE / 2)
            item_y_pos = key_data['y'] * TILE_SIZE + (TILE_SIZE / 2)
            Item(self, (item_x_pos, item_y_pos), 'key')


        self.playing = True
        self.paused = False
        self.game_over = False
        self.run()

    def run(self):
        """The main game loop."""
        while self.playing:
            self.dt = self.clock.tick(60) / 1000
            self.events()
            if not self.paused and not self.game_over and not self.player.dialogue_active:
                self.update()
            self.draw()
            
            if self.paused:
                self.show_pause_screen()
            elif self.game_over:
                self.show_death_screen()
            
            pygame.display.flip()

    def events(self):
        """Handles all game events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.playing = False
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.playing and not self.game_over:
                        self.paused = not self.paused
                        if self.paused:
                            self.ui.messages.clear()
                            self.player.dialogue_active = False
                            self.ui.clear_merchant_options()
                
                if self.player.dialogue_active:
                    self.ui.handle_merchant_input(event)


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
            if item.type == 'key':
                self.player.keys += 1
                self.add_message("Picked up a mysterious key!")
        
        # Check if player died
        if self.player.health <= 0 and not self.game_over:
            self.game_over = True
            self.playing = False
            self.add_message("You have fallen!")


    def draw(self):
        """Draws everything to the screen."""
        self.screen.fill(BLACK)

        for sprite in self.all_sprites:
            self.screen.blit(sprite.image, self.camera.apply(sprite))
            
        if self.player.attacking and self.player.equipped_item == 'sword':
            attack_rect = self.player.get_attack_rect()
            s = pygame.Surface((attack_rect.width, attack_rect.height), pygame.SRCALPHA)
            s.fill((255, 255, 0, 128))
            self.screen.blit(s, self.camera.apply_rect(attack_rect))

        self.ui.draw(self.screen)
        
    def add_message(self, text):
        """Convenience method to add a message to the UI."""
        self.ui.add_message(text)

    def show_start_screen(self):
        """Displays the start screen."""
        start_screen_running = True
        while start_screen_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    start_screen_running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if start_button_rect.collidepoint(event.pos):
                         start_screen_running = False
            
            self.screen.fill(BLACK)
            self.ui.draw_text_center(self.screen, "TOP-DOWN ADVENTURE", self.ui.large_font, WHITE, -100)
            
            start_button_rect = pygame.Rect(
                SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT / 2 + 50, 200, 50
            )
            if self.ui.draw_button(self.screen, "START GAME", start_button_rect, DARK_GREY, GREY):
                start_screen_running = False

            pygame.display.flip()
        
        if self.running:
            self.new()

    def show_pause_screen(self):
        """Displays the pause screen."""
        pause_screen_running = True
        self.ui.messages.clear()
        self.add_message("Game Paused")

        while pause_screen_running:
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            self.screen.blit(s, (0, 0))

            self.ui.draw_text_center(self.screen, "PAUSED", self.ui.large_font, WHITE, -100)

            resume_button_rect = pygame.Rect(
                SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT / 2, 200, 50
            )
            exit_button_rect = pygame.Rect(
                SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT / 2 + 70, 200, 50
            )

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.playing = False
                    pause_screen_running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pause_screen_running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if resume_button_rect.collidepoint(event.pos):
                        pause_screen_running = False
                    if exit_button_rect.collidepoint(event.pos):
                        self.running = False
                        self.playing = False
                        pause_screen_running = False

            if self.ui.draw_button(self.screen, "Resume", resume_button_rect, DARK_GREY, GREY):
                pause_screen_running = False
            
            if self.ui.draw_button(self.screen, "Exit Game", exit_button_rect, DARK_GREY, GREY):
                self.running = False
                self.playing = False
                pause_screen_running = False
            
            self.paused = pause_screen_running
            pygame.display.flip()

    def show_death_screen(self):
        """Displays the game over/death screen."""
        death_screen_running = True
        
        while death_screen_running:
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            self.screen.blit(s, (0, 0))

            self.ui.draw_text_center(self.screen, "GAME OVER", self.ui.large_font, RED, -100)

            respawn_button_rect = pygame.Rect(
                SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT / 2 + 20, 200, 50
            )
            exit_button_rect = pygame.Rect(
                SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT / 2 + 90, 200, 50
            )

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    death_screen_running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if respawn_button_rect.collidepoint(event.pos):
                        death_screen_running = False
                        self.new()
                    if exit_button_rect.collidepoint(event.pos):
                        self.running = False
                        death_screen_running = False
                        
            if self.ui.draw_button(self.screen, "Respawn", respawn_button_rect, DARK_GREY, RED):
                death_screen_running = False
                self.new()
            
            if self.ui.draw_button(self.screen, "Exit Game", exit_button_rect, DARK_GREY, RED):
                self.running = False
                death_screen_running = False

            pygame.display.flip()

# --- Main execution ---
if __name__ == '__main__':
    g = Game()
    g.show_start_screen()
    pygame.quit()
