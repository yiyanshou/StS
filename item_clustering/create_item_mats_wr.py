from sqlite3 import connect
from json import loads
import numpy as np
import pandas as pd

db_path = 'C:\\Users\\yiyan\\StS_data\\Spire.db'
file_out = 'FWWR_A20_act3_items'
wr_data = ('C:\\Users\\yiyan\\Documents\\Python\\StS\\chaining\\'
           'A20_act3_thresholds.csv')

all_data = pd.read_csv(wr_data)
high_tswr = all_data[all_data['max_fwwr'] >= 0.3]
play_ids = high_tswr['play_id']
id_str = ','.join(['\'{}\''.format(pid) for pid in play_ids])

try:
    print('Querying data...')
    con = connect(db_path)
    sql = con.execute('SELECT MasterDeck, Relics, CharacterChosen '
                            'FROM MegaCritData '
                            'WHERE PlayId IN ({}) '
                            'AND Relics NOT LIKE \'%PrismaticShard%\' '
                            'AND AdjustedFloorReached >= 52'.format(id_str))

    all_item_data = [(loads(d) + loads(r), c) for d, r, c in sql]
    
    sql = con.execute('SELECT Name, Character FROM Cards ')
    all_cards = list(sql)
    all_cards.remove(('SKIP', 'ALL'))
    all_cards.remove(('Singing Bowl', 'ALL'))
    
    sql = con.execute('SELECT Name, Character FROM Relics')
    all_relics = list(sql)
    all_relics.remove(('PrismaticShard', 'ALL'))
    
finally:
    con.close
    
def trim(s):
    return s.split('+')[0]

item_mats = []    
for char in ['IRONCLAD', 'THE_SILENT', 'DEFECT', 'WATCHER']:
    print('Assembling {} matrices...'.format(char))
    items = ([n for n, c in all_cards if c == char or c == 'ALL']
             + [n for n, c in all_relics if c == char or c == 'ALL'])
    item_data = [d for d, c in all_item_data if c == char]
    
    item_col = {}
    for i, n in enumerate(items):
        item_col[n] = i
    
    M = np.zeros((len(item_data), len(items)), dtype = int)
    for i, d in enumerate(item_data):
        for n in d:
            try:
                M[i, item_col[trim(n)]] = 1
            except KeyError:
                continue
            
    item_mats.append((M, np.array(items)))
    
np.savez(file_out,
         ironclad_mat = item_mats[0][0], ironclad_items = item_mats[0][1],
         silent_mat = item_mats[1][0], silent_items = item_mats[1][1],
         defect_mat = item_mats[2][0], defect_items = item_mats[2][1],
         watcher_mat = item_mats[3][0], watcher_items = item_mats[3][1])    
print('Done.')