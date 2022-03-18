from math import ceil
import json
import sqlite3
import gzip
from py7zr import SevenZipFile
import os
import datetime
import basic_cleaning
import gold_hp_cleaning
import campfire_shop_cleaning
import item_cleaning
import event_encounter_cleaning

# converts snake case to camel case
def snake_to_camel(s):
    words = s.split('_')
    for i, w in enumerate(words):
        if w[0].isalpha():
            first = w[0].upper()
        words[i] = first + w[1:]
    return ''.join(words)

# converts a datetime string of the form yyyy-mm-dd-hh-mm to the sqlite
# datetime string yyyy-mm-dd hh:mm
def datetime_tosqlite(s):
    parts = s.split('-')
    if not (len(parts) == 5 and len(parts[0]) == 4 and len(parts[1]) == 2
            and len(parts[2]) == 2 and len(parts[3]) == 2
            and len(parts[4]) == 2 and parts[0].isdigit()
            and parts[1].isdigit() and parts[2].isdigit()
            and parts[3].isdigit() and parts[4].isdigit()):
        raise ValueError
    return '{}-{}-{} {}:{}'.format(*parts)

# reverse of the datetime_tosql conversion
def datetime_fromsqlite(s):
    s_new = s.replace(' ', '-').replace(':', '-')
    parts = s_new.split('-')
    if not (len(parts) == 5 and len(parts[0]) == 4 and len(parts[1]) == 2
            and len(parts[2]) == 2 and len(parts[3]) == 2
            and len(parts[4]) == 2 and parts[0].isdigit()
            and parts[1].isdigit() and parts[2].isdigit()
            and parts[3].isdigit() and parts[4].isdigit()):
        raise ValueError
    return s_new

def get_dtype(o):
    if isinstance(o, bool):
        return 'bool'
    elif isinstance(o, int):
        return 'int'
    elif isinstance(o, float):
        return 'float'
    elif isinstance(o, str):
        return 'str'
    elif isinstance(o, list) or isinstance(o, dict):
        return 'json'
    else:
        raise(ValueError)
        
def to_sql(o):
    dtype = get_dtype(o)
    if dtype == 'bool':
        return (int(o), 'INT')
    elif dtype == 'json':
        return (json.dumps(o), 'TEXT')
    elif dtype == 'float':
        return (o, 'REAL')
    elif dtype == 'str':
        return (o, 'TEXT')
    else:
        return (o, 'INT')

def pipe_jsongz(dbpath, jsondir, filenames, verbose = True):
    skipped_err = []
    skipped_indb = []
    totalinserts = 0
    allcolsadded = []
    
    con = sqlite3.connect(dbpath, isolation_level = None)
    cur = con.cursor()
    
    filecnt = 1
    totalfiles = len(filenames)
    for name in filenames:
        date = name[:16]
        path = '{}\\{}'.format(jsondir, name)
        
        if verbose:
            print('importing {} ({}/{})'.format(name, filecnt, totalfiles))
            filecnt += 1
        
        query = 'SELECT InDatabase FROM Files WHERE FileDate = ?'
        try:
            indb = cur.execute(query, (datetime_tosqlite(date),)).fetchone()[0]
        except Exception as err:
            con.close()
            raise err
        if indb == 1:
            skipped_indb.append(name)
            continue
        
        cur.execute('BEGIN')
        try:
            with gzip.open(path) as jfile:
                added = _pipe_clean_json(cur, jfile, date)
            _update_meta(cur, date)
            totalinserts += added[0]
            allcolsadded += added[1]
        except Exception:
            skipped_err.append(name)
            cur.execute('ROLLBACK')
            continue
        cur.execute('COMMIT')
        
    con.close()
    
    if verbose:
        print('----------------------------\n'
              'rows inserted: {}\n\n'
              'columns added: {}\n\n'
              'skipped (already in database): {} \n\n'
              'skipped (error): {}'.format(totalinserts, allcolsadded,
                                           skipped_indb, skipped_err))
    return (totalinserts, allcolsadded)

def pipe_json7z(dbpath, archive_path, filenames, verbose = True,
                batch_size = 200):
    skipped_err = []
    skipped_indb = []
    totalinserts = 0
    allcolsadded = []
    
    con = sqlite3.connect(dbpath, isolation_level = None)
    cur = con.cursor()
    
    filecnt = 1
    totalfiles = len(filenames)
    for batch_num in range(ceil(totalfiles / batch_size)):
        batch = filenames[batch_num * batch_size:(batch_num + 1) * batch_size]
        with SevenZipFile(archive_path) as archive:
            file_dict = archive.read(batch)
            
        for name in batch:
            date = name[:16]
            
            if verbose:
                print('importing {} ({}/{})'.format(name, filecnt, totalfiles))
                filecnt += 1
            
            query = 'SELECT InDatabase FROM Files WHERE FileDate = ?'
            try:
                indb = cur.execute(query,
                                   (datetime_tosqlite(date),)).fetchone()[0]
            except Exception as err:
                con.close()
                raise err
            if indb == 1:
                skipped_indb.append(name)
                continue
            
            cur.execute('BEGIN')
            try:
                added = _pipe_clean_json(cur, file_dict[name], date)
                _update_meta(cur, date)
                totalinserts += added[0]
                allcolsadded += added[1]
            except Exception as err:  # debug
                skipped_err.append(name)
                cur.execute('ROLLBACK')
                raise err  # debug
                continue
            cur.execute('COMMIT')
        
    con.close()
    
    if verbose:
        print('----------------------------\n'
              'rows inserted: {}\n\n'
              'columns added: {}\n\n'
              'skipped (already in database): {} \n\n'
              'skipped (error): {}'.format(totalinserts, allcolsadded,
                                           skipped_indb, skipped_err))
    return (totalinserts, allcolsadded)
    
    
def _add_cols(sqlcur, table, newcols):
    colsadded = []
    query = 'SELECT name FROM pragma_table_info(\'{}\')'.format(table)
    curcols = sqlcur.execute(query).fetchall()
    
    for col, sqltype in newcols:
        if (col,) not in curcols:
            query = 'ALTER TABLE {} ADD COLUMN {} {}'.format(table, 
                                                             col, sqltype)
            sqlcur.execute(query)
            colsadded.append(col)
    return colsadded

# method for importing files from the data dump        
def _pipe_json(sqlcur, jsonrb, filedate, table = 'FullData'):
    rowsadded = 0
    colsadded = []
    jdict_raw = json.load(jsonrb)
    jdict = [jrun['event'] for jrun in jdict_raw]

    for rundict in jdict:
        keys = [snake_to_camel(key) for key in rundict.keys()]
        values = list(rundict.values())
        keystr = ','.join(keys)
        colstr = 'FileDate,' + keystr
        sqlvalues = [to_sql(val) for val in values]
        row = [datetime_tosqlite(filedate)] + [vt[0] for vt in sqlvalues]
        
        qmarks = ','.join(['?'] * len(row))
        query = 'INSERT INTO {}({}) VALUES ({})'.format(table, colstr, qmarks)
        try:
            sqlcur.execute(query, row)
            rowsadded += 1
        except sqlite3.OperationalError:
            sqltypes = [vt[1] for vt in sqlvalues]
            colsch = [(keys[i], sqltypes[i]) for i in range(len(keys))]
            colsadded += _add_cols(sqlcur, table, colsch)
            sqlcur.execute(query, row)
            rowsadded += 1
    return (rowsadded, colsadded)

# method for importing files from the data dump while performing
# data cleansing
def _pipe_clean_json(sqlcur, jsonrb, filedate, table = 'MegaCritData'):
    game_dict = {}
    
    card_names_sql = sqlcur.execute('SELECT Name FROM Cards')
    game_dict['card_names'] = [r[0] for r in card_names_sql]
    
    relic_names_sql = sqlcur.execute('SELECT Name FROM Relics')
    game_dict['relic_names'] = [r[0] for r in relic_names_sql]
    
    potion_names_sql = sqlcur.execute('SELECT Name FROM Potions')
    game_dict['potion_names'] = [r[0] for r in potion_names_sql]
    
    event_names_sql = sqlcur.execute('SELECT Name FROM Events')
    game_dict['event_names'] = [r[0] for r in event_names_sql]
    
    encounters_sql = sqlcur.execute('SELECT Name, '
                                    'MAX(NumEnemies, MaxEnemiesSplit), '
                                    'MaxGoldReward '
                                    'FROM Encounters')
    encounters = {}
    for r in encounters_sql:
        encounters[r[0]] = (r[1], r[2])
    game_dict['encounters'] = encounters
    
    rowsadded = 0
    colsadded = []
    jdict_raw = json.load(jsonrb)
    jdict = [jrun['event'] for jrun in jdict_raw]

    for rundict in jdict:
        keys = [snake_to_camel(key) for key in rundict.keys()]
        values = list(rundict.values())
        keystr = ','.join(keys)
        colstr = 'FileDate, Clean, AdjustedFloorReached, Abandoned, ' + keystr
        sqlvalues = [to_sql(val) for val in values]
        row = ([datetime_tosqlite(filedate), 
               int(_is_clean(rundict, game_dict)), 
               basic_cleaning.adjusted_floor_reached(**rundict),
               int(basic_cleaning.is_abandoned(**rundict))] 
               + [vt[0] for vt in sqlvalues])
        qmarks = ','.join(['?'] * len(row))
        query = 'INSERT INTO {}({}) VALUES ({})'.format(table, colstr, qmarks)
        try:
            sqlcur.execute(query, row)
            rowsadded += 1
        except sqlite3.OperationalError:
            sqltypes = [vt[1] for vt in sqlvalues]
            colsch = [(keys[i], sqltypes[i]) for i in range(len(keys))]
            colsadded += _add_cols(sqlcur, table, colsch)
            sqlcur.execute(query, row)
            rowsadded += 1
    return (rowsadded, colsadded)

# performs all data cleansing procedures on a run. json_dict is the json
# dictionary from the Mega Crit data set, and game_dict is a dictionary of
# game information: 
# { 'card_names':set, 'relic_names':set, 'potion_names':set,
#   'event_names':set,
#   'encounters':dict{'encounter_name':(max_fatalities, max_gold_reward)} }
def _is_clean(json_dict, game_dict):
    args_dict = json_dict.copy()
    if 'killed_by' not in json_dict:
        args_dict['killed_by'] = None
    if 'neow_bonus' not in json_dict:
        args_dict['neow_bonus'] = None
    if 'neow_cost' not in json_dict:
        args_dict['neow_cost'] = None
    return (basic_cleaning.is_clean(**args_dict)
            and campfire_shop_cleaning.is_clean(**args_dict)
            and item_cleaning.is_clean(**args_dict, **game_dict)
            and event_encounter_cleaning.is_clean(**args_dict, **game_dict)
            and gold_hp_cleaning.is_clean(**args_dict, **game_dict))

# method for importing individual .run files
def _pipe_run(sqlcur, runrb, filedate, table = 'MyData'):
    rowsadded = 0
    colsadded = []
    rundict = json.load(runrb)

    keys = list(rundict.keys())
    values = list(rundict.values())
    for i, key in enumerate(keys):
        keys[i] = snake_to_camel(key)
        
    keystr = ','.join(keys)
    colstr = 'FileDate,' + keystr
    sqlvalues = [to_sql(val) for val in values]
    row = [filedate] + [vt[0] for vt in sqlvalues]
    
    qmarks = ','.join(['?'] * len(row))
    query = 'INSERT INTO {}({}) VALUES ({})'.format(table, colstr, qmarks)
    try:
        sqlcur.execute(query, row)
        rowsadded += 1
    except sqlite3.OperationalError:
        sqltypes = [vt[1] for vt in sqlvalues]
        colsch = [(keys[i], sqltypes[i]) for i in range(len(keys))]
        colsadded += _add_cols(sqlcur, table, colsch)
        sqlcur.execute(query, row)
        rowsadded += 1
    return (rowsadded, colsadded)

def _update_meta(sqlcur, filedate, indatabase = 1):
    query = 'UPDATE Files SET InDatabase = ? WHERE FileDate = ?'
    sqlcur.execute(query, (indatabase, datetime_tosqlite(filedate)))
    return None

def pipe_personal_runs(dbpath, rundir):
    daily_files = os.listdir('{}\\{}'.format(rundir, 'DAILY'))
    ironclad_files = os.listdir('{}\\{}'.format(rundir, 'IRONCLAD'))
    silent_files = os.listdir('{}\\{}'.format(rundir, 'THE_SILENT'))
    defect_files = os.listdir('{}\\{}'.format(rundir, 'DEFECT'))
    watcher_files = os.listdir('{}\\{}'.format(rundir, 'WATCHER'))

    run_files = []
    for file in daily_files:
        if file[-4:] == '.run':
            run_files.append('{}\\{}'.format('DAILY', file))
    for file in ironclad_files:
        if file[-4:] == '.run':
            run_files.append('{}\\{}'.format('IRONCLAD', file))
    for file in silent_files:
        if file[-4:] == '.run':
            run_files.append('{}\\{}'.format('THE_SILENT', file))
    for file in defect_files:
        if file[-4:] == '.run':
            run_files.append('{}\\{}'.format('DEFECT', file))
    for file in watcher_files:
        if file[-4:] == '.run':
            run_files.append('{}\\{}'.format('WATCHER', file))
            
    nruns = len(run_files)
    print('{} runs found. Importing data...'.format(nruns))
    
    today = str(datetime.date.today())
    try:
        con = sqlite3.connect(dbpath, isolation_level = None)
        cur = con.cursor()
        cur.execute('BEGIN')
        n = 0
        
        for file in run_files:
            with open('{}\\{}'.format(rundir, file), 'r') as rb:
                _pipe_run(cur, rb, today)
           
            n += 1
            print('run imported ({}/{})'.format(n, nruns))
        
        con.commit()
        print('Complete.')
        
    except Exception as err:
        print('Error occured. Rolling back...')
        con.close()
        raise err
    finally:
        con.close()
        
def pipe_local_runs(dbpath, rundir, table):
    run_files = os.listdir(rundir)
            
    nruns = len(run_files)
    print('{} runs found. Importing data...'.format(nruns))
    
    today = str(datetime.date.today())
    try:
        con = sqlite3.connect(dbpath, isolation_level = None)
        cur = con.cursor()
        cur.execute('BEGIN')
        n = 0
        
        for file in run_files:
            with open('{}\\{}'.format(rundir, file), 'r') as rb:
                _pipe_run(cur, rb, today, table = table)
           
            n += 1
            print('run imported ({}/{})'.format(n, nruns))
        
        con.commit()
        print('Complete.')
        
    except Exception as err:
        print('Error occured. Rolling back...')
        con.close()
        raise err
    finally:
        con.close()