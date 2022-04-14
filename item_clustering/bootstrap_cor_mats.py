import numpy as np
from cor_cluster import bootstrap_pearsonr
from joblib import Parallel, delayed

file_in = 'FWWR_A20_act3_items.npz'
file_out = 'FWWR_A20_act3_boot'

item_data = np.load(file_in)
ironclad_data = item_data['ironclad_mat']
ironclad_labels = item_data['ironclad_items']
silent_data = item_data['silent_mat']
silent_labels = item_data['silent_items']
defect_data = item_data['defect_mat']
defect_labels = item_data['defect_items']
watcher_data = item_data['watcher_mat']
watcher_labels = item_data['watcher_items']

data = [ironclad_data, silent_data, defect_data, watcher_data]
labels = [ironclad_labels, silent_labels, defect_labels, watcher_labels]

# preprocess data by removing items that are too frequent or infrequent
for i in range(4):
    p = data[i].mean(axis = 0)
    inds = (p <= 0.99) & (p >= 0.01)
    data[i] = data[i][:, inds]
    labels[i] = labels[i][inds]

boot = lambda ds: bootstrap_pearsonr(ds, b = 500)
cor_boot = Parallel(n_jobs = 4, verbose = 10)(delayed(boot)(ds)
                                              for ds in data)  

np.savez(file_out, 
         ironclad_boot = cor_boot[0], ironclad_labels = labels[0],
         silent_boot = cor_boot[1], silent_labels = labels[1],
         defect_boot = cor_boot[2], defect_labels = labels[2],
         watcher_boot = cor_boot[3], watcher_labels = labels[3])