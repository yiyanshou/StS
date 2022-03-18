def events_valid(event_choices, event_names):
    for c in event_choices:
        if c['event_name'] not in event_names:
            return False
    return True

def encounters_valid(damage_taken, encounter_names):
    for d in damage_taken:
        if d['enemies'] not in encounter_names:
            return False
    return True

def killed_by_valid(killed_by, encounter_names):
    if killed_by is None:
        return True
    return killed_by in encounter_names

def is_clean(event_choices, damage_taken, killed_by,
             event_names, encounters, **kwargs):
    encounter_names = set(encounters.keys())
    try:
        return (events_valid(event_choices, event_names)
                and encounters_valid(damage_taken, encounter_names)
                and killed_by_valid(killed_by, encounter_names))
    except KeyError:
        return False
    



# ***test code***

# import sqlite3
# import json

# dbpath = 'C:\\Users\\yiyan\\Documents\\StS_data\\Spire.db'
# con = sqlite3.connect(dbpath)

# try:
#     data_sql = con.execute('SELECT Run, EventChoices, DamageTaken, KilledBy '
#                             'FROM FullData '
#                             'WHERE BuildVersion = \'2020-07-30\' '
#                             'LIMIT 100000')
    
#     event_names_sql = con.execute('SELECT Name FROM Events')
#     event_names = set([r[0] for r in event_names_sql])
    
#     encounter_names_sql = con.execute('SELECT Name FROM Encounters')
#     encounter_names = set([r[0] for r in encounter_names_sql])
    
#     sus = []
#     for r in data_sql:
#         event_choices = json.loads(r[1])
#         damage_taken = json.loads(r[2])
#         killed_by = r[3]
#         if not is_clean(event_choices, damage_taken, killed_by, event_names,
#                         encounter_names):
#             sus.append(r[0])
    
# finally:
#     con.close()
#     print(sus)