def scalars_valid(ascension_level, gold, player_experience, is_trial,
                  is_prod, is_daily, chose_seed, is_endless):
    return (0 <= ascension_level <= 20
            and 0 <= gold
            and 0 <= player_experience
            and is_trial == 0
            and is_prod == 0
            and is_daily == 0
            and chose_seed == 0
            and is_endless == 0)

def floors_valid(floor_reached, card_choices, relics_obtained, event_choices,
                 damage_taken, campfire_choices, potions_floor_usage,
                 potions_obtained, item_purchase_floors, items_purged_floors,
                 potions_floor_spawned):
    
    if not (0 <= floor_reached <= 57):
        return False
    
    try:
        for c in card_choices:
            if not (0 <= c['floor'] <= floor_reached):
                return False
            
        for r in relics_obtained:
            if not (0 <= r['floor'] <= floor_reached):
                return False
            
        for e in event_choices:
            if not (0 <= e['floor'] <= floor_reached):
                return False 
    
        for d in damage_taken:
            if not (0 <= d['floor'] <= floor_reached):
                return False
            
        for cf in campfire_choices:
            if not (0 <= cf['floor'] <= floor_reached):
                return False
                
        for p in potions_obtained:
            if not (0 <= p['floor'] <= floor_reached):
                return False
            
    except KeyError:
        return False
        
        
    for pf in potions_floor_usage:
        if not (0 <= pf <= floor_reached):
            return False
        
    for ip in item_purchase_floors:
        if not (0 <= ip <= floor_reached):
            return False
        
    for ipg in items_purged_floors:
        if not (0 <= ipg <= floor_reached):
            return False
        
    for ps in potions_floor_spawned:
        if not (0 <= ps <= floor_reached):
            return False
        
    return True


def lists_valid(floor_reached, gold_per_floor, current_hp_per_floor,
                max_hp_per_floor, path_per_floor, items_purchased,
                item_purchase_floors, items_purged, items_purged_floors,
                boss_relics):
    return (len(gold_per_floor) >= max(floor_reached - 1, 1)
            and len(current_hp_per_floor) >= max(floor_reached - 1, 1)
            and len(max_hp_per_floor) >= max(floor_reached - 1, 1)
            and len(path_per_floor) >= floor_reached - 1
            and len(items_purchased) == len(item_purchase_floors)
            and len(items_purged) == len(items_purged_floors)
            and len(boss_relics) <= 2)

def is_clean(ascension_level, gold, player_experience, is_trial,
             is_prod, is_daily, chose_seed, is_endless, floor_reached,
             card_choices, relics_obtained, event_choices, damage_taken,
             campfire_choices, potions_floor_usage, potions_obtained,
             item_purchase_floors, items_purged_floors, potions_floor_spawned,
             gold_per_floor, current_hp_per_floor, max_hp_per_floor,
             path_per_floor, items_purchased, items_purged, boss_relics,
             **kwargs):
    return (
        scalars_valid(ascension_level, gold, player_experience, is_trial,
                      is_prod, is_daily, chose_seed, is_endless)
        
        and lists_valid(floor_reached, gold_per_floor,
                        current_hp_per_floor, max_hp_per_floor,
                        path_per_floor, items_purchased,
                        item_purchase_floors, items_purged,
                        items_purged_floors, boss_relics)

        and floors_valid(floor_reached, card_choices, relics_obtained,
                 event_choices, damage_taken, campfire_choices,
                 potions_floor_usage, potions_obtained,
                 item_purchase_floors, items_purged_floors,
                 potions_floor_spawned)
            )
        
def portal_floor(event_choices, **kwargs):
    for event in event_choices:
        if event['player_choice'] == 'Took Portal':
            return int(event['floor'])
        
    return -1

def adjusted_floor_reached(event_choices, floor_reached, **kwargs):
    pf = portal_floor(event_choices)
    if pf == -1:
        return floor_reached
    else:
        return floor_reached + (49 - pf)
    
def is_abandoned(current_hp_per_floor, victory, **kwargs):
    if len(current_hp_per_floor) == 0:
        return True
    return current_hp_per_floor[-1] > 0 and victory == 0




# ***test code***
# import sqlite3
# import json

# dbpath = 'C:\\Users\\yiyan\\Documents\\StS_data\\Spire.db'
# sus = []
# try:
#     con = sqlite3.connect(dbpath)
#     data_sql = con.execute('SELECT AscensionLevel, Gold, PlayerExperience, '
#                            'IsTrial, IsProd, IsDaily, ChoseSeed, IsEndless, '
#                            'FloorReached, CardChoices, RelicsObtained, '
#                            'EventChoices, DamageTaken, CampfireChoices, '
#                            'PotionsFloorUsage, PotionsObtained, '
#                            'ItemPurchaseFloors, ItemsPurgedFloors, '
#                            'PotionsFloorSpawned, GoldPerFloor, '
#                            'CurrentHpPerFloor, MaxHpPerFloor, PathPerFloor, '
#                            'ItemsPurchased, ItemsPurged, BossRelics, '
#                            'Run '
#                            'FROM FullData LIMIT 10000')
    
#     for r_json in data_sql:
#         r_str = [str(c) for c in r_json]
#         r = list(map(json.loads, r_str))
#         if not is_clean(*r[:-1]):
#             sus.append(r[-1])
    
# finally:
#     con.close()
#     print(sus)
