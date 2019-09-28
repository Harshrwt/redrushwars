import random

class Boxes:
    """A class to represent boxes."""

    battle_box_types = ["Common", "Rare", "Epic", "Mega"]

    box_structure = {
        "gold": 0,
        "gems": 0,
        "cards": []
    }

    def __init__(self, boxes):
        if boxes in [12, 83]:
            self.box_type = self.battle_box_types[2]
        elif boxes % 5 == 0 and boxes > 0:
            self.box_type = self.battle_box_types[1]
        else:
            self.box_type = self.battle_box_types[0]

        chance = random.choice(range(1, 1000))
        if chance == 122:
            self.box_type = self.battle_box_types[3]
        
        if boxes < 121:
            boxes += 1
        else:
            boxes = 0
        
    def open_box(self, box_data:dict, multiplier:float, user_cards:dict):
        pass        
