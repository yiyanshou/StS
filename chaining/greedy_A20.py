import datetime
import sqlite3
import json

db_path = 'C:\\Users\\yiyan\\StS_data\\Spire.db'
file_out = 'A20_chains_a3.json'
lazy_file_out = 'A20_chains_a3_lazy.json'
win_floor = 52
min_len = 2
chain_win_start = int(datetime.datetime(2020, 1, 14, 0, 0).timestamp())

try:
    print('Querying data...')
    con = sqlite3.connect(db_path)
    data_sql = con.execute('SELECT PlayId, PlayerExperience, Playtime, '
                           'Timestamp, '
                           '(BuildVersion BETWEEN \'2020-01-14\' AND '
                           '\'2020-07-30\') '
                           'AND (AscensionLevel = 20) '
                           'AND (Clean = 1), '
                           'AdjustedFloorReached '
                           'FROM MegaCritData')
    
    # build dictionaries of runs for fast lookup
    print('Building dictionaries...')
    chain_data = {}
    search_data = {}
    for r in data_sql:
        if r[3] >= chain_win_start:
            if r[1] in chain_data:
                chain_data[r[1]].append(r)
            else:
                chain_data[r[1]] = [r]

        else:
            target_exp = r[1] + r[2]
            if target_exp in search_data:
                search_data[target_exp].append(r)
            else:
                search_data[target_exp] = [r]
                    
finally:
    con.close()
    
# determines if {r1, r2} is a run chain   
def links(r1, r2):
    return r1[1] + r1[2] == r2[1] and r2[3] - r2[2] >= r1[3]
    
# sieves out a chain starting with run i, stopping when a forward-collision
# occurs. n is a book-keeping variable counting the number of A20 runs in the
# chain.        
def chain(exp, k = 0, n = 0):
    source_runs = chain_data.get(exp, [])
    if len(source_runs) >= k + 1:
        ch = [source_runs.pop(k)]
    else:
        return ([], 0)
   
    nA20 = n
    target_exp = ch[0][1] + ch[0][2]
    target_runs = []
    for k, r in enumerate(chain_data.get(target_exp, [])):
        if links(ch[0], r):
            target_runs.append(k)
            nA20 += r[4]
    
    if len(target_runs) == 1:
        body = chain(target_exp, k = target_runs[0], n = nA20)
        return (ch + body[0], nA20 + body[1])
    else:
        return (ch, nA20)
    
# create chains truncating after forward-collisions. Filter chains with at
# least min_len many clean A20 runs
print('Chaining...')
cand_chains = []
exp_keys = list(chain_data.keys())
exp_keys.sort()

n = len(exp_keys)
while n > 0:
    ch, nA20 = chain(exp_keys[0])
    
    if len(ch) > 0:
        if nA20 >= min_len:
            cand_chains.append(ch)
            
        r = ch[-1]
        target_exp = r[1] + r[2]
        if target_exp in search_data:
            search_data[target_exp].append(r)
        else:
            search_data[target_exp] = [r]
            
    else:
        exp_keys.pop(0)
        n = len(exp_keys)
        continue

# Write results of lazy chaining to file.    
print('Preparing lazy JSON...')
# Perform filtering for chains of sufficiently many clean A20 runs.
lazy_chains = []
for ch in cand_chains:
    chA20 = []
    for r in ch:
        if r[4] == 1:
            chA20.append(r)
    if len(chA20) >= min_len:
        lazy_chains.append(chA20)
        
# Calculates number of wins, number of false starts, floor weighted win rate,
# and total number of floors
def winrates(ch):
    nwins = 0
    nfloors = 0
    nfalse = 0
    for r in ch:
        fr = r[5]
        
        nfloors += min(fr, win_floor)
        
        if fr >= win_floor:
            nwins += 1
            
        if nfloors == 0:
            fwwr = 0
        else:
            fwwr = win_floor * nwins / nfloors
            
        if fr == 0:
            nfalse += 1
    
    return (nwins, fwwr, nfloors, nfalse)

# Write lazy chains to JSON
lazy_chain_dicts = []
for ch in lazy_chains:
    nwins, fwwr, nfloors, nfalse = winrates(ch)
    ids = [r[0] for r in ch]
    lazy_chain_dicts.append({'play_ids':ids, 'nwins':nwins, 'fwwr':fwwr,
                             'nruns':len(ch), 'nfloors':nfloors,
                             'nfalse':nfalse})

with open(lazy_file_out, 'w') as jfile:
    jfile.write(json.JSONEncoder().encode(lazy_chain_dicts))
    
# transfer isolated runs in the chaining dict to the search dict
print('Preparing back-collision search dictionary...')
for r_arr in chain_data.values():
    for r in r_arr:
        target_exp = r[1] + r[2]
        if target_exp in search_data:
            search_data[target_exp].append(r)
        else:
            search_data[target_exp] = [r]
            
# split chains at back-collisions
print('Splitting...')
i = 0
while i < len(cand_chains):
    ch = cand_chains[i]
    for j in range(1, len(ch)):
        split = False
        colls = search_data.get(ch[j][1])
        if colls == None: 
            continue

        for r in colls:
            if links(r, ch[j]):
                split = True
                break

        if split:
            cand_chains.append(ch[j:])
            cand_chains[i] = ch[:j]
            break
    i += 1

print('Preparing JSON...')
# Perform final filtering for chains of sufficiently many clean A20 runs.
final_chains = []
for ch in cand_chains:
    chA20 = []
    for r in ch:
        if r[4] == 1:
            chA20.append(r)
    if len(chA20) >= min_len:
        final_chains.append(chA20)

# Write chains to JSON
chain_dicts = []
for ch in final_chains:
    nwins, fwwr, nfloors, nfalse = winrates(ch)
    ids = [r[0] for r in ch]
    chain_dicts.append({'play_ids':ids, 'nwins':nwins, 'fwwr':fwwr,
                        'nruns':len(ch), 'nfloors':nfloors,
                        'nfalse':nfalse})

with open(file_out, 'w') as jfile:
    jfile.write(json.JSONEncoder().encode(chain_dicts))
    
print('Complete! {} chains extracted.'.format(len(final_chains)))