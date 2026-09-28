"""Loot, drops, shop, crafting, and equipment economy."""

import random

import pygame

from systems import audio
from systems.items import buy_price, generate_item, generate_shop_stock, sell_price
from core.screen_state import GameScreen


class GameEconomyMixin:
    def spawn_drop(self, x, y, player_level, force_item=False, luck_bonus=0.0):
        roll = random.random()
        item = None
        cyc = self._difficulty()
        if force_item or roll < 0.35:  # 35% drop (élites: siempre)
            luck = min(8.0 + 1.5 * cyc + luck_bonus, player_level * 0.4 + 1.5 * cyc + luck_bonus)
            item = generate_item(max(1, player_level + random.randint(-1, 1)), luck=luck)
        gold = int(round((random.randint(2, 6) + player_level * 1.5) * (1 + 0.3 * cyc)))
        self.drops.append({'item': item, 'rect': pygame.Rect(x, y, 14, 14),
                           'vy': -260.0, 'gold': gold, 't': 0.0})

    # --- Eventos ---

    def _shop_luck(self):
        return 4.0 + 1.5 * self._difficulty()

    def _open_shop(self):
        p = self.player
        if not self.shop_stock or self.shop_level != p.level:
            self.shop_stock = generate_shop_stock(p.level, luck=self._shop_luck())
            self.shop_level = p.level
        self.shop_tab = 'buy'
        self.set_screen(GameScreen.SHOP)

    def _shop_buy(self, item_id):
        p = self.player
        for i, it in enumerate(self.shop_stock):
            if it.get('id') == item_id:
                price = buy_price(it)
                if p.gold < price:
                    self.inv_message = f"Oro insuficiente ({price}g)"
                    self.inv_message_t = 2.0
                    return
                p.spend_gold(price)
                p.add_item(it)
                self.shop_stock[i] = generate_item(max(1, p.level), slot=it.get('slot'), luck=self._shop_luck())
                self.inv_message = f"Comprado: {it.get('name')} (-{price}g)"
                self.inv_message_t = 2.5
                return

    def _shop_sell(self, item_id):
        p = self.player
        for i, it in enumerate(p.inventory):
            if it.get('id') == item_id:
                price = sell_price(it)
                del p.inventory[i]
                p.add_gold(price)
                self.inv_message = f"Vendido: {it.get('name')} (+{price}g)"
                self.inv_message_t = 2.5
                return

    def _shop_upgrade(self, item_id):
        from systems.items import upgrade_cost, apply_upgrade, MAX_UPGRADE
        p = self.player
        target = None
        for it in list(p.equipment.values()) + p.inventory:
            if it is not None and it.get('id') == item_id:
                target = it
                break
        if target is None:
            return
        from systems.items import upgrade_level
        if upgrade_level(target) >= MAX_UPGRADE:
            self.inv_message = "Nivel máximo de mejora (+8)"
            self.inv_message_t = 2.0
            return
        cost = upgrade_cost(target)
        if not p.spend_gold(cost):
            self.inv_message = f"Oro insuficiente ({cost}g)"
            self.inv_message_t = 2.0
            return
        apply_upgrade(target)
        p.recalculate_stats()
        audio.play('buy', 0.9)
        self.fx.burst(p.rect.centerx, p.rect.centery, n=14, color=(255, 220, 100),
                      speed=170.0, life=0.5, grav=100.0)
        self.inv_message = f"Mejorado: {target.get('name')} (-{cost}g)"
        self.inv_message_t = 2.5

    def _shop_craft(self, slot, rarity):
        from systems.items import craft_result_rarity, generate_item
        p = self.player
        nxt = craft_result_rarity(rarity)
        if nxt is None:
            return
        cands = [it for it in p.inventory
                 if it.get('slot') == slot and it.get('rarity') == rarity]
        if len(cands) < 3:
            self.inv_message = "Necesitas 3 piezas iguales"
            self.inv_message_t = 2.0
            return
        # Fundir las 3 de menor poder
        from systems.items import item_power
        cands.sort(key=item_power)
        for it in cands[:3]:
            p.inventory.remove(it)
        new_item = generate_item(max(1, p.level), slot=slot, rarity=nxt, luck=2.0)
        p.add_item(new_item)
        audio.play('skill')
        self.fx.burst(p.rect.centerx, p.rect.centery, n=20, color=(200, 120, 255),
                      speed=200.0, life=0.6, grav=100.0)
        self.inv_message = f"Forjado: {new_item.get('name')}"
        self.inv_message_t = 2.5

    def update_drops(self, dt):
        from constants import GRAVITY as _G
        p = self.player
        for d in list(self.drops):
            d['t'] += dt
            # Física simple del drop
            d['vy'] += _G * dt * 0.6
            d['rect'].y += int(round(d['vy'] * dt))
            if self.game_map.check_collision(d['rect']):
                d['rect'].y -= int(round(d['vy'] * dt))
                d['vy'] = 0
            # Pickup por proximidad
            if p and d['rect'].colliderect(p.rect.inflate(12, 12)):
                if d['item'] is not None:
                    p.add_item(d['item'])
                    self.inv_message = f"Recogido: {d['item']['name']}"
                    self.inv_message_t = 2.5
                    audio.play('pickup')
                    self.fx.burst(d['rect'].centerx, d['rect'].centery, n=10,
                                color=(150, 220, 255), speed=140.0, life=0.4, grav=100.0)
                g = p.add_gold(d['gold'])
                if d['gold']:
                    audio.play('coin', 0.7)
                    self.texts.add(p.rect.centerx, p.rect.top - 4, f"+{g}g", (255, 220, 100))
                self.drops.remove(d)
        if self.inv_message_t > 0:
            self.inv_message_t -= dt
