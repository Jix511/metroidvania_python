"""NPC proximity, reactive dialogue, quest acceptance and completion."""

import pygame

from core.screen_state import GameScreen
from systems import audio
from systems.npc_data import NPCS, dialogue_for, npc_position
from systems.quest_data import QUESTS, quest_status
from systems.rewards import grant_reward, reward_summary


class GameNarrativeMixin:
    def nearest_npc(self, radius=90):
        if self.player is None:
            return None
        best, best_distance = None, radius * radius
        for npc_id, npc in NPCS.items():
            x, y = npc_position(self.player, npc)
            dx = self.player.rect.centerx - x
            dy = self.player.rect.centery - y
            distance = dx * dx + dy * dy
            if distance <= best_distance:
                best, best_distance = npc_id, distance
        return best

    def _pending_npc_quest(self, npc_id):
        if self.player is None:
            return None
        for wanted in ('ready', 'available'):
            for quest_id, quest in QUESTS.items():
                if quest['giver'] == npc_id and quest_status(self.player, quest_id) == wanted:
                    return quest_id, wanted
        return None

    def npc_quest_marker(self, npc_id):
        pending = self._pending_npc_quest(npc_id)
        return pending[1] if pending else None

    def npc_prompt_text(self, npc_id):
        npc = NPCS[npc_id]
        verb = 'Hablar' if self._pending_npc_quest(npc_id) else 'Conversar'
        return f'F: {verb} con {npc["name"].split(",")[0]}'

    def _begin_dialogue(self, npc_id, pages, action='close', quest_id=None, choices=None):
        self.dialogue_npc_id = npc_id
        self.dialogue_quest_id = quest_id
        self.dialogue_action = action
        self.dialogue_pages = list(pages)
        self.dialogue_page = 0
        self.dialogue_started_at = pygame.time.get_ticks()
        self.dialogue_choices = list(choices or [])
        self.dialogue_choice = 0
        self.set_screen(GameScreen.DIALOGUE)
        audio.play('click', 0.6)

    def interact_npc(self, npc_id):
        pending = self._pending_npc_quest(npc_id)
        if pending is not None:
            quest_id, status = pending
            quest = QUESTS[quest_id]
            action = 'complete' if status == 'ready' else 'accept'
            self._begin_dialogue(npc_id, quest['dialogue'][status], action, quest_id)
            return
        npc = NPCS[npc_id]
        choices = [('Escuchar', 'talk'), ('Despedirse', 'leave')]
        if npc['role'] == 'shopkeeper':
            choices = [('Conversar', 'talk'), ('Abrir tienda', 'shop')]
        self._begin_dialogue(npc_id, dialogue_for(self.player, npc), choices=choices)

    def move_dialogue_choice(self, direction):
        if self.dialogue_choices:
            self.dialogue_choice = (self.dialogue_choice + direction) % len(self.dialogue_choices)
            audio.play('click', 0.4)

    def choose_dialogue_option(self):
        if not self.dialogue_choices:
            self.advance_dialogue()
            return
        _label, action = self.dialogue_choices[self.dialogue_choice]
        npc = NPCS[self.dialogue_npc_id]
        if action == 'shop':
            self.dialogue_choices = []
            self._open_shop()
        elif action == 'talk':
            self.dialogue_choices = []
            self.dialogue_pages = list(npc['lore'])
            self.dialogue_page = 0
            self.dialogue_started_at = pygame.time.get_ticks()
        else:
            self._close_dialogue()

    def _close_dialogue(self):
        self.dialogue_pages = []
        self.dialogue_choices = []
        self.dialogue_page = 0
        self.dialogue_npc_id = None
        self.dialogue_quest_id = None
        self.dialogue_action = None
        self.set_screen(GameScreen.GAMEPLAY)

    def advance_dialogue(self):
        if self.screen_state is not GameScreen.DIALOGUE:
            return
        line = self.dialogue_pages[self.dialogue_page]
        elapsed = pygame.time.get_ticks() - self.dialogue_started_at
        if int(elapsed * 0.05) < len(line):
            self.dialogue_started_at = pygame.time.get_ticks() - len(line) * 20
            return
        if self.dialogue_choices:
            self.choose_dialogue_option()
            return
        self.dialogue_page += 1
        if self.dialogue_page < len(self.dialogue_pages):
            self.dialogue_started_at = pygame.time.get_ticks()
            audio.play('click', 0.5)
            return
        quest_id = self.dialogue_quest_id
        if self.dialogue_action == 'accept':
            self.player.quest_states[quest_id] = 'active'
            self.inv_message = f'Misión aceptada: {QUESTS[quest_id]["title"]}'
        elif self.dialogue_action == 'complete':
            result = grant_reward(self.player, QUESTS[quest_id]['reward'],
                                  item_level=self.player.level)
            for item in result['items']:
                self.player.add_item(item)
            self.player.quest_states[quest_id] = 'completed'
            self.inv_message = (f'Misión completada: {QUESTS[quest_id]["title"]} · '
                                f'{reward_summary(result)}')
            npc = NPCS[self.dialogue_npc_id]
            if npc.get('rescue_quest') == quest_id:
                self.inv_message += ' · Se unió al refugio'
        self.inv_message_t = 4.0
        self._close_dialogue()
        audio.play('quest' if quest_id else 'click', 0.8)
