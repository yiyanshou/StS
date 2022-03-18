def trim_card_name(name):
    ind_plus = name.find('+')
    if ind_plus >= 0:
        return name[:ind_plus]
    else:
        return name

def is_clean(master_deck, card_choices, items_purchased, items_purged,
             event_choices, relics, relics_obtained, boss_relics,
             potions_obtained, card_names, relic_names, potion_names,
             **kwargs):
    cards_chosen = []
    cards_skipped = []
    for c in card_choices:
        cards_chosen.append(c['picked'])
        cards_skipped += c['not_picked']
        
    relics_chosen = []
    relics_skipped = []
    for br in boss_relics:
        if 'picked' in br:
            relics_chosen.append(br['picked'])
        relics_skipped += br['not_picked']
    
    event_cards = []
    event_relics = []
    event_potions = []
    for c in event_choices:
        if 'cards_obtained' in c:
            event_cards += c['cards_obtained']
        if 'cards_removed' in c:
            event_cards += c['cards_removed']
        if 'cards_transformed' in c:
            event_cards += c['cards_transformed']
        if 'relics_obtained' in c:
            event_relics += c['relics_obtained']
        if 'relics_removed' in c:
            event_relics += c['relics_lost']
        if 'potions_obtained' in c:
            event_potions += c['potions_obtained']
            
    all_items = set(master_deck + items_purged + cards_chosen + cards_skipped
                    + event_cards + relics_chosen + relics_skipped
                    + event_relics + event_potions + items_purchased)
    
    for name in all_items:
        trimmed_name = trim_card_name(name)
        if ((trimmed_name not in card_names)
            and (trimmed_name not in relic_names) 
            and (trimmed_name not in potion_names)):
            return False
        
    return True
    
    
    
    

# ***test code***

# import sqlite3
# import json

# dbpath = 'C:\\Users\\yiyan\\Documents\\StS_data\\Spire.db'
# con = sqlite3.connect(dbpath)

# try:
#     data_sql = con.execute('SELECT Run, MasterDeck, CardChoices, '
#                            'ItemsPurchased, ItemsPurged, EventChoices, '
#                            'Relics, RelicsObtained, BossRelics, '
#                            'PotionsObtained '
#                            'FROM FullData '
#                            'WHERE BuildVersion = \'2020-07-30\' '
#                            'LIMIT 500000')
    
#     card_names_sql = con.execute('SELECT Name FROM Cards')
#     card_names = [r[0] for r in card_names_sql]
    
#     relic_names_sql = con.execute('SELECT Name FROM Relics')
#     relic_names = [r[0] for r in relic_names_sql]
    
#     potion_names_sql = con.execute('SELECT Name FROM Potions')
#     potion_names = [r[0] for r in potion_names_sql]
    
#     data = None
#     sus = []
#     for r in data_sql:
#         master_deck = json.loads(r[1])
#         card_choices = json.loads(r[2])
#         items_purchased = json.loads(r[3])
#         items_purged = json.loads(r[4])
#         event_choices = json.loads(r[5])
#         relics = json.loads(r[6])
#         relics_obtained = json.loads(r[7])
#         boss_relics = json.loads(r[8])
#         potions_obtained = json.loads(r[9])
#         if not is_clean(master_deck, card_choices, items_purchased,
#                         items_purged, event_choices, relics, relics_obtained,
#                         boss_relics, potions_obtained,
#                         card_names, relic_names, potion_names):
#             sus.append(r[0])

# finally:
#     con.close()
#     print(sus)
