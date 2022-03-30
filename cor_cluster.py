# Module for hierarchical clustering of Bernoulli random variables based on
# Pearson correlation.
import numpy as np
import scipy.stats as sps
from itertools import product
from matplotlib import pyplot as plt
from joblib import Parallel, delayed

# Sparse tensor representation of a higher dimensional contingency table
class ContingencyTable:
    def __init__(self, data = None, counts = None):
        self._counts = {}
        self._n = 0
        self._d = 0
        
        if counts is not None:
            self._counts = counts
            for t, c in counts.items():
                self._n += c
                self._d = len(t)
                
        elif data is not None:
            self._n, self._d = data.shape
            for r in data.astype(int):
                t = tuple(r)
                if t in self._counts:
                    self._counts[t] += 1
                else:
                    self._counts[t] = 1
                    
        p = []
        self._multinomial_vals = []
        for t, c in self._counts.items():
            self._multinomial_vals.append(t)
            p.append(c / self._n) 
        self._rv = sps.rv_discrete(values = (range(len(self._counts)), p))

        self.n = self._n
        self.d = self._d
                    
    def count(self, t):
        return self._counts.get(t, 0)
    
    def proportion(self, t):
        return self.count(t) / self._n
    
    def array(self, proportions = False):
        arr = np.zeros([2] * self._d, dtype = int)
        for t, c in self._counts.items():
            arr[t] = c
            
        if proportions:
            return arr.astype(float) / self._n
        else:
            return arr
    
    def sum(self, axis = None):
        if axis is None:
            axis = range(self._d)
        try:
            iter(axis)
            _axis = list(axis)
        except TypeError:
            _axis = [axis]
        
        new_axes = list(range(self._d))
        for i in _axis:
            new_axes.remove(i)
            
        sum_counts = {}
        for t, c in self._counts.items():
            sum_t = tuple(np.array(t)[new_axes])
            if sum_t in sum_counts:
                sum_counts[sum_t] += c
            else:
                sum_counts[sum_t] = c
                
        return ContingencyTable(counts = sum_counts)

    def cor(self, i = 0, j = 1):
        if i == j:
            return 1.0
        
        sum_axes = list(range(self._d))
        sum_axes.remove(i)
        sum_axes.remove(j)
        ct = self.sum(sum_axes)
        
        p1 = ct.sum(0).proportion((1,))
        p2 = ct.sum(1).proportion((1,))
            
        num = ct.proportion((1, 1)) - p1 * p2
        den = np.sqrt(p1 * p2 * (1 - p1) * (1 - p2))
        return max(min(num / den, 1.0), 0)  

    def average_cor(self, pairs = None):
        if pairs is None:
            pairs = [(i, j) for i in range(self._d)
                            for j in range(i + 1, self._d)]
            
        cor_sum = 0.0
        for i, j in pairs:
            cor_sum += self.cor(i, j)
            
        return cor_sum / len(pairs)
    
    def bootstrap(self):
        rep = []
        for i in self._rv.rvs(size = self._n):
            rep.append(self._multinomial_vals[i])
        return ContingencyTable(data = np.array(rep))
    
    

# Monotone transformation that turns Pearson correlation into a bonafide
# distance metric.        
def metric_transform(rho):
    return np.sqrt(2 * (1 - rho))

# Helper function that compares the average linkage of pairs of clusters to
# a fixed null pair
def _diffs_average(ct, clusters, null_pair):
    i0, j0 = null_pair
    other_pairs = [(i, j) for i in range(len(clusters))
                          for j in range(i + 1, len(clusters))]
    other_pairs.remove((i0, j0))
    avg_pairs = list(product(clusters[i0], clusters[j0]))
    null_val = ct.average_cor(avg_pairs)
    
    other_vals = np.zeros(len(other_pairs))
    for j, (k, l) in enumerate(other_pairs):
        avg_pairs = list(product(clusters[k], clusters[l]))
        other_vals[j] = ct.average_cor(avg_pairs)
        
    return other_vals - null_val

# Runs a one-sided Ward test on the difference in average linkage between
# pairs of clusters and a null pair. Test statistic is computed using
# a bootstrap estimate of standard error with b replicates.
def ward_test_average(ct, clusters, null_pair, b = 500, n_jobs = -1):
    if null_pair[0] > null_pair[1]:
        null_pair = (null_pair[1], null_pair[0])
    
    nclusters = len(clusters)
    nother = int(( nclusters * (nclusters - 1) / 2 ) - 1)
    boot = lambda _:_diffs_average(ct.bootstrap(), clusters, null_pair)
    print('bootstrapping')
    draws = np.array(Parallel(n_jobs = n_jobs, verbose = 51)
                     (delayed(boot)() for i in range(b)))
    se_boot = draws.std(axis = 0)
    ests = _diffs_average(ct, clusters, null_pair)
    return 1 - sps.norm.cdf(np.abs(ests) / se_boot)

# Pearson correlation based average linkage hierachical clustering with
# stopping condition based on Wald test with bootstrapped standard errors.
# Optionally, transform correlation to a true distance metric. Output is
# a scipy.cluster.hierarchy style linkage matrix.
def average_linkage(data, alpha = 0.05, b = 500, metric = False):
    ct = ContingencyTable(data = data)
    d = ct.d
    
    # mappings between matrix and flat indexing
    mat = {}
    flat = {}
    k = 0
    for i in range(d):
        for j in range(i + 1, d):
            flat[(i, j)] = k
            mat[k] = (i, j)
            k += 1
    
    # need to keep track of members of each cluster for bootstrapping
    clusters = [[i] for i in range(d)]
    linkage_inds = list(range(d))
    
    # initialize flattened matrix of correlations/distance
    D = np.zeros(int( d * (d - 1) / 2 ))
    for (i, j), k in flat.items():
        D[k] = ct.cor(i, j)
    if metric:
        D = metric_transform(D)
    
    Z = []
    for iz in range(d - 1):
        # find closest pair of variables
        if metric:
            arg_opt = D.argmin()
            D_opt = D[arg_opt]
            closest_pair = mat[arg_opt]
        else:
            arg_opt = D.argmax()
            D_opt = D[arg_opt]
            closest_pair = mat[arg_opt]
        
        # check stopping condition (Ward test with Bonferroni correction)
        pvals = ward_test_average(ct, clusters, closest_pair, b = b)
        if (pvals >= alpha / d).any():
            break
        
        # update clusters and linkage matrix
        i0, j0 = closest_pair
        Z.append([linkage_inds[i0], linkage_inds[j0],
                  D_opt, len(clusters[i0]) + len(clusters[j0])])
        clusters[i0] += clusters[j0]
        clusters.pop(j0)
        linkage_inds[i0] = d + iz
        linkage_inds.pop(j0)
        
        # update D
        if metric:
            for k in range(i0 + 1, d - iz - 1):
                avg_pairs = list(product(clusters[i0], clusters[k]))
                D[flat[(i0, k)]] = metric_transform(ct.average_cor(avg_pairs))
            for k in range(i0):
                avg_pairs = list(product(clusters[k], clusters[i0]))
                D[flat[(k, i)]] = metric_transform(ct.average_cor(avg_pairs))
        else:
            for k in range(i0 + 1, d - iz - 1):
                avg_pairs = list(product(clusters[i0], clusters[k]))
                D[flat[(i0, k)]] = ct.average_cor(avg_pairs)
            for k in range(i0):
                avg_pairs = list(product(clusters[k], clusters[i0]))
                D[flat[(k, i0)]] = ct.average_cor(avg_pairs)
                
        new_flat_inds = []
        for i in range(d - iz):
            for j in range(i + 1, d - iz):
                if i != j0 and j != j0:
                    new_flat_inds.append(flat[(i, j)])    
        D = D[new_flat_inds]
        
        # update mappings between matrix and flat indices
        k = 0
        for i in range(d - iz - 1):
            for j in range(i + 1, d - iz - 1):
                flat[(i, j)] = k
                mat[k] = (i, j)
                k += 1
            
    return Z

# Plot the (truncated) dendrogram corresponding to (partial) linkage matrix Z
def dendrogram(Z, labels, metric = False, orientation = 'v', **kwargs):
    n = len(labels)
    node_pos = np.zeros((len(Z) + n, 2))
    leaves = []
    if metric:
        leaf_pos = np.array([0.0, 0.0])
    else:
        leaf_pos = np.array([0.0, 1.0])
    
    for i, (c1, c2, d, _) in enumerate(Z):
        for c in (c1, c2):
            if c < n:
                leaves.append(c)
                node_pos[c] = leaf_pos
                leaf_pos += np.array([1.0, 0.0])
                
        node_pos[i + n, 0] = (node_pos[c1, 0] + node_pos[c2, 0]) / 2
        node_pos[i + n, 1] = d
        
        pos1 = node_pos[c1]
        pos2 = node_pos[c2]
        if orientation == 'v':
            plt.plot([pos1[0], pos1[0]], [pos1[1], d], 'b')
            plt.plot([pos2[0], pos2[0]], [pos2[1], d], 'b')
            plt.plot([pos1[0], pos2[0]], [d, d], 'b')
        else:
            plt.plot([pos1[1], d], [pos1[0], pos1[0]], 'b')
            plt.plot([pos2[1], d], [pos2[0], pos2[0]], 'b')
            plt.plot([d, d], [pos1[0], pos2[0]], 'b')
    
    if orientation == 'v':
        labels = [labels[i] for i in leaves]
        plt.gca().set_xticks(range(len(leaves)))
        plt.gca().set_xticklabels(labels)
        if not metric:
            plt.gca().invert_yaxis()
    elif orientation == 'h':
        labels = [labels[i] for i in leaves]
        plt.gca().set_yticks(range(len(leaves)))
        plt.gca().set_yticklabels(labels)
        if not metric:
            plt.gca().invert_xaxis()   
    else:
        raise ValueError