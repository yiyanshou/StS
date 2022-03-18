def is_clean(campfire_choices, items_purged_floors, **kwargs):
    c_floors = set()
    for c in campfire_choices:
        fl = c['floor']
        if fl in c_floors:
            return False
        c_floors.add(fl)
    
    distinct_p_floors = set(items_purged_floors)
    if len(distinct_p_floors) < len(items_purged_floors):
        return False
        
    return True



# ***test code***

# import sqlite3
# import json

# dbpath = 'C:\\Users\\yiyan\\Documents\\StS_data\\Spire.db'

# try:
#     con = sqlite3.connect(dbpath)
#     sql = con.execute('SELECT Run, CampfireChoices, ItemsPurgedFloors '
#                       'FROM FullData '
#                       'WHERE BuildVersion = \'2020-07-30\' LIMIT 100000')
    
#     sus = []
#     for r in sql:
#         campfire_choices = json.loads(r[1])
#         items_purged_floors = json.loads(r[2])
#         if not is_clean(campfire_choices, items_purged_floors):
#             sus.append(r[0])
        
# finally:
#     con.close()
#     print(sus)
