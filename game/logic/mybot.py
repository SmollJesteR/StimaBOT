from game.logic.base import BaseLogic
from game.models import Board, GameObject, Position
from typing import Optional
from ..util import get_direction
import random
import math

class MyBot(BaseLogic):
    def __init__(self):
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        self.goal_position: Optional[Position] = None  #posisi goal
        self.current_direction = 0 #posisi sekarang
        self.chased_timer = 0 #atribut untuk menghitung berapa banyak waktu dikejar bot lain
        self.last_position: Optional[Position] = None # posisi terakhir sebagai counter stuck program
        self.run = 0 #dodge count
        self.diamound_counter_cd = 0  # Cooldown setelah sampai area diamond
        self.stuck_counter = 0 #counter stuck program

    def next_move(self, board_bot: GameObject, board: Board):
        props = board_bot.properties
        current_position = board_bot.position
        all_bots = board.bots
        diamonds = board.diamonds

        #menghitung berapa banyak diamond disekitar diamond yang menjadi target
        def count_near_diamond_target(center: Position, radius: int = 3) -> int:
            return sum(
                1 for d in diamonds
                if abs(d.position.x - center.x) + abs(d.position.y - center.y) <= radius
            )

        #menghitung jarak
        def distance(pos1: Position, pos2: Position) -> int:
            return math.hypot(pos1.x - pos2.x, pos1.y - pos2.y)

        #deteksi bot disekitar player didalam area jangkauan 2 blok
        def steal(radius: int = 2):
            return [
                bot for bot in all_bots
                if bot.id != board_bot.id and
                abs(bot.position.x - current_position.x) + abs(bot.position.y - current_position.y) <= radius
            ]

        nearby_bots = steal(radius=2)

        # Update chased timer
        self.chased_timer = self.chased_timer + 1 if nearby_bots else 0

        # Update diamond focus timer
        if self.diamound_counter_cd > 0:
            self.diamound_counter_cd -= 1

        # Update stuck detection
        if self.last_position == current_position:
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0

        self.last_position = current_position

        # Jika stuck selama 2 tick, ubah arah dan reset goal
        if self.stuck_counter >= 2:
            self.goal_position = None
            self.current_direction = (self.current_direction + 1) % len(self.directions)
            delta_x, delta_y = self.directions[self.current_direction]
            return delta_x, delta_y

        # Force pulang kalau dikejar selama 5 tick
        if self.chased_timer >= 5:
            base = props.base
            self.goal_position = base
            delta_x, delta_y = get_direction(current_position.x, current_position.y, base.x, base.y)
            return delta_x, delta_y

        # Jika sudah punya ≥4 berlian: pulang ke base (sekali dodge lalu kabur)
        if props.diamonds >= 4:
            base = props.base
            if nearby_bots and self.run <= 2:
                closest = min(nearby_bots, key=lambda b: distance(current_position, b.position))
                dx = current_position.x - closest.position.x
                dy = current_position.y - closest.position.y
                dodge_x = 1 if dx >= 0 else -1
                dodge_y = 1 if dy >= 0 else -1
                self.goal_position = Position(
                    min(max(0, base.x + dodge_x), board.width - 1),
                    min(max(0, base.y + dodge_y), board.height - 1),
                )
                self.run += 1  # Setelah dodge, kabur ke base
            else:
                self.goal_position = base
                self.run += 1
                if self.run >= 5:
                    self.run = 0

            delta_x, delta_y = get_direction(current_position.x, current_position.y, self.goal_position.x, self.goal_position.y)
            return delta_x, delta_y

        # Coba curi berlian dari bot lain
        enemy_carry_diamond = [
            bot for bot in all_bots
            if bot.id != board_bot.id
            and bot.properties.diamonds >= 2
            and distance(current_position, bot.position) <= 4
        ]

        if enemy_carry_diamond:
            target = max(enemy_carry_diamond, key=lambda b: b.properties.diamonds)
            if target.position != props.base:  # Hindari musuh di atas base kita
                self.goal_position = target.position
                delta_x, delta_y = get_direction(current_position.x, current_position.y, self.goal_position.x, self.goal_position.y)
                return delta_x, delta_y

        # Jika tidak dalam cooldown, cari diamond terbaik
        if self.diamound_counter_cd == 0:
            candidate_diamonds = [
            d for d in diamonds if distance(current_position, d.position) <= 5
        ]

            best_diamond = max(
                candidate_diamonds,
                key=lambda d: (
                    count_near_diamond_target(d.position, radius=2),
                    -distance(current_position, d.position)
                ),
                default=None
            )

            if best_diamond:
                self.goal_position = best_diamond.position
            elif diamonds:
                nearest = min(diamonds, key=lambda d: distance(current_position, d.position))
                self.goal_position = nearest.position
            else:
                self.goal_position = None

        # Jika sedang cooldown, tapi ada diamond dekat (radius ≤ 2), tetap ambil
        elif self.diamound_counter_cd > 0:
            close_diamonds = [
                d for d in diamonds if distance(current_position, d.position) <= 2
            ]
            if close_diamonds:
                nearest = min(close_diamonds, key=lambda d: distance(current_position, d.position))
                self.goal_position = nearest.position


        # Bergerak ke goal atau roaming
        if self.goal_position and self.goal_position != current_position:
            delta_x, delta_y = get_direction(current_position.x, current_position.y, self.goal_position.x, self.goal_position.y)

            # Aktifkan cooldown jika sudah sampai ke goal
            if self.goal_position == current_position:
                self.diamound_counter_cd = 4

        else:
            delta = self.directions[self.current_direction]
            delta_x, delta_y = delta
            if random.random() > 0.6:
                self.current_direction = (self.current_direction + 1) % len(self.directions)

        return delta_x, delta_y
