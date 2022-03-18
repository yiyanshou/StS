import numpy as np

def relic_changes(relics_obtained, boss_relics, event_choices, relics,
                  neow_bonus, items_purchased, item_purchase_floors,
                  relic_names):

    if (neow_bonus == 'RANDOM_COMMON_RELIC' 
        or neow_bonus == 'THREE_ENEMY_KILL'
        or neow_bonus == 'ONE_RARE_RELIC'):
        starting_relics = relics[0:2]
    else:
        starting_relics = [relics[0]]
    
    rc = {0:[set(starting_relics), set()]}
        
    for d in relics_obtained:
        floor = int(d['floor'])
        rel = d['key']
        if floor not in rc:
            rc[floor] = [set(), set()]
        rc[floor][0].add(rel)
    
    for i, d in enumerate(boss_relics):
        if 'picked' in d:
            rel = d['picked']
            if i == 0:
                floor = 17
            elif i == 1:
                floor = 34
            if floor not in rc:
                rc[floor] = [set(), set()]
            rc[floor][0].add(rel)
        
            if rel == 'Black Blood':
                rc[floor][1].add('Burning Blood')
            elif rel == 'Ring of the Serpent':
                rc[floor][1].add('Ring of the Snake')
            elif rel == 'FrozenCore':
                rc[floor][1].add('Cracked Core')
            elif rel == 'HolyWater':
                rc[floor][1].add('PureWater')           
            
    for d in event_choices:
        rels = set()
        rels_lost = set()
        if 'relics_obtained' in d:
            rels = set(d['relics_obtained'])
        if 'relics_lost' in d:
            rels_lost = set(d['relics_lost'])
        floor = int(d['floor'])
        if floor not in rc:
            rc[floor] = [set(), set()]
        rc[floor][0] |= rels
        rc[floor][1] |= rels_lost
            
    for i in range(len(items_purchased)):
        item = items_purchased[i]
        floor = item_purchase_floors[i]
        if item in relic_names:
            if floor not in rc:
                rc[floor] = [set(), set()]
            rc[floor][0].add(item)
            
    return rc

def relics_by_floor(relic_changes, floor_reached):
    if floor_reached == 0:
        return []
    
    rbf = [None] * (floor_reached + 1)
    rbf[0] = relic_changes[0][0]
    
    for i in range(1, floor_reached + 1):
        if i in relic_changes:
            rbf[i] = (rbf[i - 1] | relic_changes[i][0]) - relic_changes[i][1]
        else:
            rbf[i] = rbf[i - 1]
        
    return rbf

def trim_card(card_name):
    upgrade_ind = card_name.find('+')
    if upgrade_ind >= 0:
        return card_name[:upgrade_ind]
    else:
        return card_name

def earliest_gold_hp_cards(card_choices, event_choices,
                           items_purchased, item_purchase_floors,
                           neow_bonus, relic_changes, character_chosen):
    
    unlogged_additions = []
    unlogged_removals = []
    unlogged_transforms = []
    hog_floor = 57
    wish_floor = 57
    feed_floor = 57
    prismatic_floor = 57
    
    neow_removals = {'REMOVE_CARD', 'REMOVE_TWO'}
    neow_transforms = {'TRANSFORM_CARD', 'TRANSFORM_TWO_CARDS'}
    if neow_bonus == 'ONE_RANDOM_RARE_CARD':
        unlogged_additions.append(0)
    elif neow_bonus in neow_removals:
        unlogged_removals.append(0)
    elif neow_bonus in neow_transforms:
        unlogged_transforms.append(0)
        
    for floor in iter(relic_changes):
        relics_gained = relic_changes[floor][0]
        if 'Tiny House' in relics_gained:
            unlogged_additions.append(floor)
        if 'Empty Cage' in relics_gained:
            unlogged_removals.append(floor)
        if 'Pandora\'s Box' in relics_gained or 'Astrolabe' in relics_gained:
            unlogged_transforms.append(floor)
        if 'PrismaticShard' in relics_gained:
            prismatic_floor = floor
        if 'Nilry\'s Codex' in relics_gained or 'Dead Branch' in relics_gained:
            hog_floor = min(hog_floor, floor)
            
    if character_chosen == 'IRONCLAD':
        min_wish_floor = prismatic_floor
        min_feed_floor = 0
    elif character_chosen == 'THE_SILENT' or character_chosen == 'DEFECT':
        min_wish_floor = prismatic_floor
        min_feed_floor = prismatic_floor
    elif character_chosen == 'WATCHER':
        min_wish_floor = 0
        min_feed_floor = prismatic_floor
            
    for choice in card_choices:
        picked = trim_card(choice['picked'])
        floor = int(choice['floor'])
        if picked == 'HandOfGreed':
            hog_floor = min(hog_floor, floor)
        elif picked == 'Wish':
            wish_floor = min(wish_floor, floor)
        elif picked == 'Feed':
            feed_floor = min(feed_floor, floor)
            
    for event in event_choices:
        if 'cards_obtained' in event:
            floor = int(event['floor'])
            card_reward = [trim_card(card) 
                           for card in event['cards_obtained']]
            if 'HandOfGreed' in card_reward:
                hog_floor = min(hog_floor, floor)
            if 'Wish' in card_reward:
                wish_floor = min(wish_floor, floor)
            if 'Feed' in card_reward:
                feed_floor = min(feed_floor, floor)
        
        if 'cards_transformed' in event:
            unlogged_transforms.append(int(event['floor']))

    for i, item in enumerate(items_purchased):
        if trim_card(item) == 'HandOfGreed':
            hog_floor = min(hog_floor, item_purchase_floors[i])
        elif trim_card(item) == 'Wish':
            wish_floor = min(wish_floor, item_purchase_floors[i])           
        elif trim_card(item) == 'Feed':
            feed_floor = min(feed_floor, item_purchase_floors[i])
            
    for floor in unlogged_additions + unlogged_transforms:
        hog_floor = min(hog_floor, floor)
        if min_wish_floor <= floor:
            wish_floor = min(wish_floor, floor)
        if min_feed_floor <= floor:
            feed_floor = min(feed_floor, floor)
            
    return (hog_floor, feed_floor, wish_floor)
        
def current_hp_isvalid(current_hp_per_floor, max_hp_per_floor):
    isvalid = True
    for i, cur_hp in enumerate(current_hp_per_floor):
        if cur_hp > max_hp_per_floor[i]:
            isvalid = False
    return isvalid

def fruit_juice_hp(relic_changes, potions_obtained, items_purchased, 
                   item_purchase_floors, event_choices, floor_reached):
    bark_floor = 57
    for floor in iter(relic_changes):
        if 'SacredBark' in relic_changes[floor][0]:
            bark_floor = floor
            
    hp_by_floor = np.zeros(floor_reached + 1, dtype = int)
    
    for pot in potions_obtained:
        if pot['key'] == 'Fruit Juice':
            floor = int(pot['floor'])
            hp_by_floor[floor] += 5 * (1 + (bark_floor >= floor))
            
    for i, item in enumerate(items_purchased):
        if item == 'Fruit Juice':
            floor = item_purchase_floors[i]
            hp_by_floor[floor] += 5 * (1 + (bark_floor >= floor))
            
    for event in event_choices:
        if 'potions_obtained' in event:
            potions = event['potions_obtained']
            for pot in potions:
                if pot == 'Fruit Juice':
                    floor = int(event['floor'])
                    hp_by_floor[floor] += 5 * (1 + (bark_floor >= floor))
                    
    # fruit juice obtained through Entropic Brew cannot be tracked.
    extra = 10
    hp_by_floor[0] += extra * 5 * (1 + (bark_floor >= floor))
                    
    return hp_by_floor
                    
def neow_gold(neow_bonus, neow_cost):
    if neow_cost == 'NO_GOLD':
        gold = 0
    else:
        gold = 99
        
    if neow_bonus == 'HUNDRED_GOLD':
        gold += 100
    elif neow_bonus == 'TWO_FIFTY_GOLD':
        gold += 250
        
    return gold

def neow_hp(neow_bonus, neow_cost, character_chosen):
    hp = 0
    
    if character_chosen == 'IRONCLAD':
        hp = 80
    elif character_chosen == 'THE_SILENT':
        hp = 70
    elif character_chosen == 'DEFECT':
        hp = 75
    else:
        hp = 72
        
    if neow_bonus == 'TEN_PERCENT_HP_BONUS':
        hp = np.ceil(1.1 * hp)
    elif neow_bonus == 'TWENTY_PERCENT_HP_BONUS':
        hp = np.ceil(1.2 * hp)
        
    if neow_cost == 'TEN_PERCENT_HP_LOSS':
        hp = np.ceil(0.9 * hp)
        
    return hp

def periapt_hp(master_deck, relic_changes, event_choices, items_purged,
               campfire_choices):
    astrolabe = False
    cage = False
    periapt = False
    mirror = False
    for rels, _ in iter(relic_changes.values()):
        if 'Astrolabe' in rels:
            astrolabe = True
        if 'Empty Cage' in rels:
            cage = True
        if 'Darkstone Periapt' in rels:
            periapt = True
        if 'DollysMirror' in rels:
            mirror = True
            
    if not periapt:
        return 0
    
    curses = {'Injury', 'Shame', 'Doubt', 'Regret', 'Pain', 'Necronomicurse',
              'AscendersBane', 'Parasite', 'Pride', 'Clumsy', 'Writhe',
              'CurseOfTheBell', 'Decay', 'Normality'}
    num_curses = 2 * cage + 3 * astrolabe + mirror
    
    for card in master_deck:
        if card in curses:
            num_curses += 1
            
    for card in items_purged:
        if card in curses:
            num_curses += 1
            
    for event in event_choices:
        if 'cards_removed' in event:
            for card in event['cards_removed']:
                if card in curses:
                    num_curses += 1
                    
        if 'cards_transformed' in event:
            for card in event['cards_transformed']:
                if card in curses:
                    num_curses += 1
                    
    for fire in campfire_choices:
        if fire['key'] == 'PURGE' and fire['data'] in curses:
            num_curses += 1
            
    return num_curses * 6

# encounters = {encounter_name:(max_fatalities, max_gold_reward)}
def combat_gold_hp(damage_taken, floor_reached, encounters, relics_by_floor, 
                   greed_floor, feed_floor, wish_floor):
    gold_by_floor = np.zeros(floor_reached + 1, dtype = float)
    hp_by_floor = np.zeros(floor_reached + 1, dtype = float)
    
    for dmg in damage_taken:
        if 'floor' in dmg and 'enemies' in dmg:
            floor = int(dmg['floor'])
            enc_name = dmg['enemies']
            
            max_fat, max_gold = encounters[enc_name]
            gold = max_gold * (1 + 0.25 * ('Golden Idol' in 
                                           relics_by_floor[floor - 1]))
            gold_by_floor[floor] += np.ceil(gold)
            
            if True:
                gold_by_floor[floor] += 25 * max_fat
            if wish_floor < floor:
                gold_by_floor[floor] += np.inf
            if feed_floor < floor:
                hp_by_floor[floor] += 4 * max_fat
                
            if 'FaceOfCleric' in relics_by_floor[floor - 1]:
                hp_by_floor[floor] += 1
                
    return (gold_by_floor, hp_by_floor)

def chest_gold(path_per_floor, event_choices, floor_reached):
    gold_by_floor = np.zeros(floor_reached + 1, dtype = float)
    
    event_floors = set()
    for event in event_choices:
        event_floors.add(int(event['floor']))
        
    for i, room in enumerate(path_per_floor):
        if room == 'T' or (room == '?' and (i + 1 not in event_floors)):
            gold_by_floor[i + 1] += 82

    return gold_by_floor
    
def event_gold_hp(event_choices, floor_reached):
    hp_by_floor = np.zeros(floor_reached + 1, dtype = float)
    gold_by_floor = np.zeros(floor_reached + 1, dtype = float)
    for event in event_choices:
        floor = int(event['floor'])
        if 'max_hp_gain' in event:
            hp_by_floor[floor] += event['max_hp_gain']
        if 'max_hp_loss' in event:
            hp_by_floor[floor] -= event['max_hp_loss']
        if 'gold_gain' in event:
            gold_by_floor[floor] += event['gold_gain']
        if 'gold_loss' in event:
            gold_by_floor[floor] -= event['gold_loss']
        if event['event_name'] == 'Dead Adventurer':
            gold_by_floor[floor] += 30
            
    return (gold_by_floor, hp_by_floor)

def relic_gold_hp(relic_changes, card_choices, event_choices,
                  path_per_floor, items_purchased, item_purchase_floors,
                  floor_reached, card_names):
    gold_by_floor = np.zeros(floor_reached + 1, dtype = float)
    hp_by_floor = np.zeros(floor_reached + 1, dtype = float)
    key_floor = -1
    fish_floor = -1
    house_floor = -1
    box_floor = -1
    astrolabe_floor = -1
    bell_floor = -1
    necro_floor = -1
    serpent_floor = -1
    maw_floor = -1
    idol_floor = -1
    mirror_floor = -1
    has_bowl = False
    for floor in relic_changes:
        relics_added = relic_changes[floor][0]
        if 'Old Coin' in relics_added:
            gold_by_floor[floor] += 300
        if 'Strawberry' in relics_added:
            hp_by_floor[floor] += 7
        if 'Pear' in relics_added:
            hp_by_floor[floor] += 10
        if 'Mango' in relics_added:
            hp_by_floor[floor] += 14
        if 'Lee\'s Waffle' in relics_added:
            hp_by_floor[floor] += 7
            
        if 'Cursed Key' in relics_added:
            key_floor = floor
        if 'CeramicFish' in relics_added:
            fish_floor = floor
        if 'Pandora\'s Box' in relics_added:
            box_floor = floor
        if 'Astrolabe' in relics_added:
            astrolabe_floor = floor
        if 'Calling Bell' in relics_added:
            bell_floor = floor
        if 'Necronomicon' in relics_added:
            necro_floor = floor
        if 'SsserpentHead' in relics_added:
            serpent_floor = floor
        if 'MawBank' in relics_added:
            maw_floor = floor
        if 'Golden Idol' in relics_added:
            idol_floor = floor
        if 'DollysMirror' in relics_added:
            mirror_floor = floor
            
        if 'Tiny House' in relics_added:
            gold_by_floor[floor] += 50
            hp_by_floor[floor] += 5
            house_floor = floor
        if 'Singing Bowl' in relics_added:
            has_bowl = True
    
    # it seems Golden Idol affects the Tiny House gold bonus (glitch?)
    if idol_floor >= 0 and house_floor >= 0 and idol_floor <= house_floor:
        gold_by_floor[house_floor] += 13
        
    if fish_floor >= 0 or has_bowl == True:
        for card in card_choices:
            floor = int(card['floor'])
            if floor >= fish_floor:
                gold_by_floor[floor] += 9
            if has_bowl and card['picked'] == 'Singing Bowl':
                hp_by_floor[floor] += 2
                
    if fish_floor >= 0:
        if house_floor >= fish_floor:
            gold_by_floor[house_floor] += 9
        if bell_floor >= fish_floor:
            gold_by_floor[bell_floor] += 9
        if necro_floor >= fish_floor:
            gold_by_floor[necro_floor] += 9
        if astrolabe_floor >= fish_floor:
            gold_by_floor[astrolabe_floor] += 9 * 3
        if box_floor >= fish_floor:
            gold_by_floor[box_floor] += 9 * 11
        if mirror_floor >= fish_floor:
            gold_by_floor[mirror_floor] += 9
            
        for event in event_choices:
            floor = int(event['floor'])
            if floor < fish_floor:
                continue
            if 'cards_obtained' in event:
                gold_by_floor[floor] += 9 * len(event['cards_obtained'])
            if 'cards_transformed' in event:
                gold_by_floor[floor] += 9 * len(event['cards_transformed'])

        for i, item in enumerate(items_purchased):
            floor = item_purchase_floors[i]
            if floor >= fish_floor and item in card_names:
                gold_by_floor[floor] += 9
                
        if key_floor >= 0:
            start_floor = max(key_floor, fish_floor)
            for floor in range(start_floor, floor_reached + 1):
                if path_per_floor[floor - 1] == 'T' or path_per_floor == '?':
                    gold_by_floor[floor] += 9
                    
    if serpent_floor >= 0:
        for floor in range(serpent_floor, floor_reached + 1):
            if (path_per_floor[floor - 1] == '?' 
                or path_per_floor[floor - 1] == 'M'
                or path_per_floor[floor - 1] == 'T'
                or path_per_floor[floor - 1] == '$'):
                gold_by_floor[floor] += 50
                
    if maw_floor >= 0:
        for floor in range(maw_floor, floor_reached + 1):
            gold_by_floor[floor] += 12
            
    return (gold_by_floor, hp_by_floor)

                        
def max_gold_hp(card_choices, event_choices, relics_obtained, boss_relics,
                damage_taken, campfire_choices, items_purchased, items_purged,
                item_purchase_floors, potions_obtained, neow_bonus, neow_cost,
                relics, master_deck, path_per_floor, character_chosen,
                floor_reached, relic_names, card_names, encounters):
    
    if floor_reached <= 2:
        cutoff = 2
    elif path_per_floor[-1] == '?':
        cutoff = floor_reached - 1
    else:
        cutoff = floor_reached
    
    max_gold = np.zeros(cutoff, dtype = float)
    max_hp = 0
    
    _relic_changes = relic_changes(relics_obtained, boss_relics, event_choices,
                                  relics, neow_bonus, items_purchased,
                                  item_purchase_floors, relic_names)
    _relics_by_floor = relics_by_floor(_relic_changes, floor_reached)
    earliest = earliest_gold_hp_cards(card_choices, event_choices,
                                      items_purchased, item_purchase_floors,
                                      neow_bonus, _relic_changes,
                                      character_chosen)
    greed_floor, feed_floor, wish_floor = earliest
    
    max_gold[0] += neow_gold(neow_bonus, neow_cost)
    max_hp += neow_hp(neow_bonus, neow_cost, character_chosen)
    
    max_hp += periapt_hp(master_deck, _relic_changes, event_choices,
                         items_purged, campfire_choices)
    
    max_hp += fruit_juice_hp(_relic_changes, potions_obtained, items_purchased,
                             item_purchase_floors, event_choices,
                             floor_reached)[:cutoff].sum()
    
    max_gold += chest_gold(path_per_floor, event_choices,
                           floor_reached)[:cutoff]
    
    combat_gold, combat_hp = combat_gold_hp(damage_taken, floor_reached,
                                            encounters, _relics_by_floor,
                                            greed_floor, feed_floor,
                                            wish_floor)
    max_gold += combat_gold[:cutoff]
    max_hp += combat_hp[:cutoff].sum()
    
    event_gold, event_hp = event_gold_hp(event_choices, floor_reached)
    max_gold += event_gold[:cutoff]
    max_hp += event_hp[:cutoff].sum()
    
    relic_gold, relic_hp = relic_gold_hp(_relic_changes, card_choices,
                                         event_choices, path_per_floor,
                                         items_purchased, item_purchase_floors,
                                         floor_reached, card_names)
    max_gold += relic_gold[:cutoff]
    max_hp += relic_hp[:cutoff].sum()
    
    return (max_gold, max_hp)

def gold_max_hp_valid(gold_per_floor, max_hp_per_floor, card_choices,
                      event_choices, relics_obtained, boss_relics,
                      damage_taken, campfire_choices, items_purchased,
                      items_purged, item_purchase_floors, potions_obtained, 
                      neow_bonus, neow_cost, relics, master_deck,
                      path_per_floor, character_chosen, floor_reached,
                      relic_names, card_names, encounters, **kwargs):
    
    gold_by_floor = np.zeros(len(gold_per_floor))
    gold_by_floor[0] = gold_per_floor[0]
    for i in range(1, len(gold_per_floor)):
        gold_by_floor[i] = gold_per_floor[i] - gold_per_floor[i - 1]
    
    try:
        max_gold, max_hp = max_gold_hp(card_choices, event_choices,
                                        relics_obtained, boss_relics,
                                        damage_taken, campfire_choices,
                                        items_purchased, items_purged,
                                        item_purchase_floors,
                                        potions_obtained, neow_bonus,
                                        neow_cost,
                                        relics, master_deck, path_per_floor,
                                        character_chosen, floor_reached,
                                        relic_names, card_names, encounters)
    except IndexError:
        return False
    except KeyError:
        return False
    
    max_gold_by_floor = np.zeros(len(max_gold) - 1)
    if len(max_gold) <= 1:
        max_gold_by_floor = max_gold
    else:
        max_gold_by_floor[0] = max_gold[0] + max_gold[1]
        max_gold_by_floor[1:] = max_gold[2:]
    
    mask = (max_gold_by_floor < gold_by_floor[:len(max_gold_by_floor)])
    if mask.any():
        return False
    
    ending_max_hp = max_hp_per_floor[len(max_gold_by_floor) - 1]
    if max_hp < ending_max_hp:
        return False
    
    return True
    
def current_hp_valid(current_hp_per_floor, max_hp_per_floor, **kwargs):
    chp = np.array(current_hp_per_floor)
    mhp = np.array(max_hp_per_floor)
    return (chp <= mhp).all()

def is_clean(gold_per_floor, max_hp_per_floor, card_choices,
             event_choices, relics_obtained, boss_relics,
             damage_taken, campfire_choices, items_purchased,
             items_purged, item_purchase_floors, potions_obtained, 
             neow_bonus, neow_cost, relics, master_deck,
             path_per_floor, character_chosen, floor_reached,
             relic_names, card_names, encounters, current_hp_per_floor,
             **kwargs):
    return (
        current_hp_valid(current_hp_per_floor, max_hp_per_floor)
        and gold_max_hp_valid(gold_per_floor, max_hp_per_floor, card_choices, 
                              event_choices, relics_obtained, boss_relics,
                              damage_taken, campfire_choices, items_purchased,
                              items_purged, item_purchase_floors,
                              potions_obtained, neow_bonus, neow_cost, relics, 
                              master_deck, path_per_floor, character_chosen, 
                              floor_reached, relic_names, card_names,
                              encounters, **kwargs)
        )
    



# ***test code***

# import sqlite3
# import json
    
# dbpath = 'C:\\Users\\yiyan\\Documents\\StS_data\\Spire.db'
# table = 'SilentV2_1'

# sus_gold_runs = []
# sus_hp_runs = []
# sus_floor_runs = []
# try:
#     con = sqlite3.connect(dbpath)
#     data_sql = con.execute('SELECT Name FROM Cards')
#     card_names = [r[0] for r in data_sql]
    
#     data_sql = con.execute('SELECT Name FROM Relics')
#     relic_names = [r[0] for r in data_sql]
    
#     data_sql = con.execute('SELECT Name, '
#                            'max(NumEnemies, MaxEnemiesSplit), '
#                            'MaxGoldReward FROM Encounters')
#     encounters = {}
#     for r in data_sql:
#         encounters[r[0]] = (r[1], r[2])
    
#     data_sql = con.execute('SELECT Run, GoldPerFloor, MaxHpPerFloor, '
#                            'CardChoices, EventChoices, RelicsObtained, '
#                            'BossRelics, DamageTaken, CampfireChoices, '
#                            'ItemsPurchased, ItemsPurged, '
#                            'ItemPurchaseFloors, PotionsObtained, '
#                            'NeowBonus, NeowCost, Relics, MasterDeck, '
#                            'PathPerFloor, CharacterChosen, FloorReached '
#                            'FROM {} '
#                            'LIMIT 100000'.format(table))
    
#     for r in data_sql:
#         run = r[0]
#         gold_per_floor = json.loads(r[1])
#         max_hp_per_floor = json.loads(r[2])
#         card_choices = json.loads(r[3])
#         event_choices = json.loads(r[4])
#         relics_obtained = json.loads(r[5])
#         boss_relics = json.loads(r[6])
#         damage_taken = json.loads(r[7])
#         campfire_choices = json.loads(r[8])
#         items_purchased = json.loads(r[9])
#         items_purged = json.loads(r[10])
#         item_purchase_floors = json.loads(r[11])
#         potions_obtained = json.loads(r[12])
#         neow_bonus = r[13]
#         neow_cost = r[14]
#         relics = json.loads(r[15])
#         master_deck = json.loads(r[16])
#         path_per_floor = json.loads(r[17])
#         character_chosen = r[18]
#         floor_reached = r[19]
        
#         gold_by_floor = np.zeros(len(gold_per_floor))
#         gold_by_floor[0] = gold_per_floor[0]
#         for i in range(1, len(gold_per_floor)):
#             gold_by_floor[i] = gold_per_floor[i] - gold_per_floor[i - 1]
        
#         try:
#             max_gold, max_hp = max_gold_hp(card_choices, event_choices,
#                                            relics_obtained, boss_relics,
#                                            damage_taken, campfire_choices,
#                                            items_purchased, items_purged,
#                                            item_purchase_floors,
#                                            potions_obtained, neow_bonus,
#                                            neow_cost,
#                                            relics, master_deck, path_per_floor,
#                                            character_chosen, floor_reached,
#                                            relic_names, card_names, encounters)
#         except IndexError:
#             sus_floor_runs.append(run)
#             continue
#         except KeyError:
#             sus_floor_runs.append(run)
#             continue
        
#         max_gold_by_floor = np.zeros(len(max_gold) - 1)
#         if len(max_gold) <= 1:
#             max_gold_by_floor = max_gold
#         else:
#             max_gold_by_floor[0] = max_gold[0] + max_gold[1]
#             max_gold_by_floor[1:] = max_gold[2:]
        
#         mask = (max_gold_by_floor < gold_by_floor[:len(max_gold_by_floor)])
#         for i, unbounded in enumerate(mask):
#             if unbounded:
#                 error_ind = i
#                 break
        
#         if mask.any():
#             summary = (run, gold_by_floor, max_gold_by_floor, error_ind)
#             sus_gold_runs.append(summary)
        
#         ending_max_hp = max_hp_per_floor[len(max_gold_by_floor) - 1]
#         if max_hp < ending_max_hp:
#             sus_hp_runs.append((run, ending_max_hp, max_hp))
        
# finally:
#     con.close()

# with open('sus_gold.txt', 'w') as f:
#     for r in sus_gold_runs: 
#         f.write('run: {}\n'
#                 'gold gain:\n{}\n'
#                 'max gold gain:\n{}\n'
#                 'first error: {}\n\n'.format(*r))

# for r in sus_hp_runs:
#     print('run: {}\n'
#           'ending max hp:\n{}\n'
#           'bound:\n{}\n'.format(*r))
 
# print('broken floor indices')
# for r in sus_floor_runs:
#     print(r)
