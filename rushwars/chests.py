import random

class Chests:
    """A class to represent chests."""

    battle_chest_types = ["Common", "Rare", "Epic", "Mega"]

    chest_structure = {
        "gold": 0,
        "gems": 0,
        "cards": []
    }

    def __init__(self, chests):
        if chests in [12, 83]:
            chest_type = self.battle_chest_types[2]
        elif chests % 5 == 0:
            chest_type = self.battle_chest_types[1]
        else:
            chest_type = self.battle_chest_types[0]

        chance = random.choice(range(1, 1000))
        if chance == 122:
            chest_type = self.battle_chest_types[3]
        
        if chests < 121:
            chests += 1
        else:
            chests = 0
        
    def open_chest(self, chest_data, user_data):
        pass
