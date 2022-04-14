# Module for hierarchical clustering of Bernoulli random variables based on
# Pearson correlation.
import numpy as np
import scipy.stats as sps
from matplotlib import pyplot as plt
import scipy.cluster.hierarchy as sch

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
    
class _ProgressMeter:
    def __init__(self, ntasks, interval = 10):
        self._i = 0
        self._n = ntasks
        self._cur = 0
        self._interval = interval
        return None
    
    def tick(self, print_update = False):
        self._i += 1
        prog = int(100 * self._i 
                   / (self._n * self._interval)) * self._interval
        if prog > self._cur:
            self._cur = prog
            if print_update:
                print('current progress: {}%'.format(self._cur))
            return self._cur
        return None
    
# helper function that puts a pair of distinct indices in ascending order
def pair(i, j):
    if i < j:
        return (i, j)
    elif j < i:
        return (j, i)
    else:
        raise ValueError
        
# create a mapping from matrix coordinates to flat coordinates
def flat(d):
    fd = {}
    k = 0
    for i in range(d):
        for j in range(i + 1, d):
            fd[(i, j)] = k
            k += 1
    return fd
    
def average_linkage(D, flat, cluster_sizes, i, j, k):
    d_sum = np.zeros(len(D))
    d_sum += cluster_sizes[i] * cluster_sizes[k] * D[:, flat[pair(i, k)]]
    d_sum += cluster_sizes[j] * cluster_sizes[k] * D[:, flat[pair(j, k)]]
    new_cluster_size = cluster_sizes[k] * (cluster_sizes[i]
                                           + cluster_sizes[j])
    return d_sum / new_cluster_size

# Monotone transformation that turns Pearson correlation into a bonafide
# distance metric.        
def metric_transform(rho):
    return np.sqrt(2 * (1 - rho))

# Helper function that compares the linkage of pairs of clusters to
# a fixed null pair
def _compare_linkages(D, flat, cluster_sizes, null_pair):
    nclusters = len(cluster_sizes)
    null_flat_ind = flat[null_pair]
    other_pairs = [(i, j) for i in range(nclusters)
                          for j in range(i + 1, nclusters)]
    other_pairs.remove(null_pair)
    other_flat_inds = [flat[p] for p in other_pairs]
    
    null_val = D[:, null_flat_ind]
    other_vals = D[:, other_flat_inds]
    diffs = np.zeros(other_vals.shape)
    for i in range(other_vals.shape[1]):
        diffs[:, i] = other_vals[:, i] - null_val
        
    return diffs

# Estimates Pearson correlation from binary data
def pearsonr(x, y):
    n = len(x)
    nxy = (x * y).sum()
    nx = x.sum()
    ny = y.sum()
    
    pxy = nxy / n
    px = nx / n
    py = ny / n
    
    num = pxy - px * py
    den = np.sqrt(px * py * (1 - px) * (1 - py))
    return max(min(num / den, 1), -1)

# Runs a one-sided Ward test on the difference in average linkage between
# pairs of clusters and a null pair. Test statistic is computed using
# a bootstrap estimate of standard error with b replicates.
def _ward_test_average(D, flat, cluster_sizes, null_pair):   
    comps = _compare_linkages(D, flat, cluster_sizes, null_pair)
    se_boot = comps[1:].std(axis = 0)
    ests = comps[0]
    return 1 - sps.norm.cdf(np.abs(ests) / se_boot)

# estimates flattened correlation matrix from data
def _flat_pearsonr(data, flat):
    n = len(data)
    D = np.zeros(len(flat))
    p = data.mean(axis = 0)
    for (j, k), l in flat.items():
        pxy = (data[:, j] * data[:, k]).sum() / n
        num = pxy - p[j] * p[k]
        den = np.sqrt(p[j] * p[k] * (1 - p[j]) * (1 - p[k]))
        D[l] = max(min(num / den, 1), -1)
    return D

# Bootstrap flattened Pearson correlation matrices. The matrix for the
# original data is recorded as the first row of the output.
def bootstrap_pearsonr(data, b = 500, verbose = False):
    d = data.shape[1]
    # mappings between matrix and flat indexing
    flat = {}
    k = 0
    for i in range(d):
        for j in range(i + 1, d):
            flat[(i, j)] = k
            k += 1
            
    if verbose:
        pm = _ProgressMeter(b)
        print('Bootstrapping b = {} replicates...'.format(b))
    
    D_boot = np.zeros((b, len(flat)))
    for i in range(b):
        boot_inds = np.random.choice(len(data), size = len(data),
                                     replace = True)
        D_boot[i] = _flat_pearsonr(data[boot_inds], flat)
        
        if verbose:
            pm.tick(True)
                                  
    D_og = _flat_pearsonr(data, flat)
    D = np.zeros(((b + 1), len(flat)))
    D[0] = D_og
    D[1:] = D_boot
    return D
    

# Hierarchical clustering of random variables based on correlation or a proper
# distance metric with stopping condition given by a Wald test with 
# bootstrapped standard errors. D is a matrix such that each row is a
# flattened distance matrix. The first row corresponds to the original data,
# and subsequent rows correspond to bootstrap replicates.
def cluster(D, linkage = average_linkage, alpha = 0.05, stop = 0,
            metric = False):
    # calculate number of variables being clustered
    d = int(np.around( (1 + np.sqrt(1 + 8 * D.shape[1])) / 2 ))
    
    # determine stopping condition
    if np.issubdtype(type(stop), np.integer):
        sc = 0
    elif np.issubdtype(type(stop), np.floating):
        sc = 1
    elif stop == 'mean':
        sc = 2

    # mappings between matrix and flat indexing
    mat = {}
    flat = {}
    k = 0
    for i in range(d):
        for j in range(i + 1, d):
            flat[(i, j)] = k
            mat[k] = (i, j)
            k += 1
    
    # keep track of clusters for updating D
    linkage_inds = list(range(d))
    cluster_sizes = [1] * d
    
    # run agglomerative hierarchical clustering algorithm
    Z = []
    for iz in range(d - 1):
        # find closest pair of variables
        if metric:
            arg_opt = D[0].argmin()
            D_opt = D[0, arg_opt]
            closest_pair = mat[arg_opt]
        else:
            arg_opt = D[0].argmax()
            D_opt = D[0, arg_opt]
            closest_pair = mat[arg_opt]
        
        # check stopping condition (Ward test)
        if D.shape[0] > 0:
            pvals = _ward_test_average(D, flat, cluster_sizes, closest_pair)
            if sc == 0:
                if (pvals >= alpha).sum() > stop:
                    break
            elif sc == 1:
                if np.quantile(pvals, stop) >= alpha:
                    break
            elif sc == 2:
                if pvals.mean() >= alpha:
                    break
            else:
                if stop(pvals):
                    break
                    
        
        # update Z
        i0, j0 = closest_pair
        size = 0
        for i in (i0, j0):
            l = linkage_inds[i]
            if l < d:
                size += 1
            else:
                size += Z[l - d][3]
            
        Z.append([linkage_inds[i0], linkage_inds[j0],
                  D_opt, size])
        
        # update D
        for k in range(d - iz):
            if k != i0 and k != j0:
                new_linkage = linkage(D, flat, cluster_sizes, i0, j0, k)
                D[:, flat[pair(i0, k)]] = new_linkage
                
        new_flat_inds = []
        for i in range(d - iz):
            for j in range(i + 1, d - iz):
                if i != j0 and j != j0:
                    new_flat_inds.append(flat[(i, j)])    
        D = D[:, new_flat_inds]
        
        # update cluster info
        linkage_inds[i0] = d + iz
        linkage_inds.pop(j0)
        if j0 < d:
            cluster_sizes[i0] += 1
        else:
            cluster_sizes[i0] += cluster_sizes[j0]
        cluster_sizes.pop(j0)
        
        # update mappings between matrix and flat indices
        k = 0
        for i in range(d - iz - 1):
            for j in range(i + 1, d - iz - 1):
                flat[(i, j)] = k
                mat[k] = (i, j)
                k += 1

    return np.array(Z)
        
# split a partial linkage matrix into proper linkage matrices
def split_linkage(Z, labels, linkage_inds = None):
    
    if linkage_inds is None:
        linkage_inds = list(range(len(Z)))
    if len(linkage_inds) == 0:
        return []
    
    linkage_inds.sort()
    n = len(labels)
    
    def descendants(i):
        if i < n:
            return [i]
        
        j, k = Z[i - n, :2]
        return descendants(int(j)) + descendants(int(k)) + [i]
    
    cluster_inds = descendants(linkage_inds[-1] + n)
    cluster_inds.sort()
    new_ind = {}
    new_labels = []
    new_Z = []
    new_linkage_inds = linkage_inds
    for i in cluster_inds:
        new_ind[i] = len(new_ind)
        if i < n:
            new_labels.append(labels[i])
        else:
            j, k, *rest = Z[i - n]
            new_Z.append([new_ind[int(j)], new_ind[int(k)], *rest])
            new_linkage_inds.remove(i - n)
    new_Z = np.array(new_Z)

    return split_linkage(Z, labels, new_linkage_inds) + [(new_Z, new_labels)]

# sorts split linkages either by size or by minimum dissimilarity between
# leaves
def sort_linkages(splits, sort_type, desc = False):
    sort_vals = np.zeros(len(splits))
    if sort_type == 'size':
        for i, (_, labels) in enumerate(splits):
            sort_vals[i] = len(labels)
    elif sort_type == 'min':
        for i, (Z, _) in enumerate(splits):
            sort_vals[i] = Z[:, 2].min()
    elif sort_type == 'max':
        for i, (Z, _) in enumerate(splits):
            sort_vals[i] = Z[:, 2].max()
    elif sort_type == 'mean':
        for i, (Z, _) in enumerate(splits):
            sort_vals[i] = Z[:, 2].mean()
    else:
        raise ValueError
        
    argsort = np.argsort(sort_vals)
    if desc:
        argsort = np.flip(argsort)
    return [splits[i] for i in argsort]

def is_monotonic(Z, metric = False):
    if metric:
        linkages = Z[:, 2]
    else:
        linkages = 1 - Z[:, 2]
    for i in range(1, len(linkages)):
        if linkages[i] <= linkages[i - 1]:
            return False
    return True
            
# plot split dendrograms
def dendrogram(splits, metric = False, orientation = 'v', color = 'b',
               show_text = False, cmap = None,
               text_args = {}, tick_args = {}, dendrogram_args = {}):
    sorted_labels = []
    offset = 0
    for Z, labels in splits:
        if not is_monotonic(Z, metric = metric):
            print('Warning: nonmonotonic linkage given. Duplicate linkage '
                  'values may cause issues with alpha and text plotting.')
        if not metric:
            _Z = Z.copy()
            _Z[:, 2] = 1 - _Z[:, 2]
        else:
            _Z = Z
        dend = sch.dendrogram(_Z[:, :4], labels = labels, no_plot = True)
        X = np.array(dend['icoord'])
        Y = np.array(dend['dcoord'])
        sorted_labels += dend['ivl']
        
        # sort link coordinates to agree with Z (only works if Z is monotonic)
        y_sort = np.argsort(Y[:, 1])
        X = X[y_sort]
        Y = Y[y_sort]
        
        X += offset
        offset = X.max() + 5
        if not metric:
            Y = 1 - Y
            
        if Z.shape[1] >= 5 and cmap is not None:
            grad = cmap(Z[:, 4])
        else:
            grad = [color] * len(Z)
        
            
        ndx = (X[:, 0] + X[:, 3]) / 2
        ndy = Y[:, 1]
        
        if orientation == 'v':
            for i in range(len(X)):
                plt.plot(X[i], Y[i], color = grad[i])
                if Z.shape[1] >= 5 and show_text:
                    plt.text(ndx[i], ndy[i], Z[i, 4], ha = 'center',
                             va = 'top', **text_args)
        elif orientation == 'h':
            for i in range(len(X)):
                plt.plot(Y[i], X[i], color = grad[i])
                if Z.shape[1] >= 5 and show_text:
                    plt.text(ndy[i], ndx[i], Z[i, 4], ha = 'right',
                             va = 'center', **text_args)
        else:
            raise ValueError

    if orientation == 'v':
        plt.gca().set_xticks(np.arange(5, 10 * len(sorted_labels), 10))
        plt.gca().set_xticklabels(sorted_labels, **tick_args)
        plt.xlim(0, offset)
        if not metric:
            plt.gca().invert_yaxis()
    else:
        plt.gca().set_yticks(np.arange(5, 10 * len(sorted_labels), 10))
        plt.gca().set_yticklabels(sorted_labels, **tick_args)
        plt.ylim(0, offset)
        if not metric:
            plt.gca().invert_xaxis()
            
    return None
   
# semi-labeled rooted binary tree logic
class Node:
    def __init__(self, child1 = None, child2 = None, label = None):
        self._parent = None
        self._children = [nd for nd in [child1, child2]
                          if nd is not None]
        for c in self._children:
            c._parent = self
        self._label = label
        return None
    
    def parent(self):
        return self._parent
    
    def children(self):
        return self._children.copy()
    
    def label(self):
        return self._label
    
    def __str__(self):
        if self.label is None:
            return '[Node]'
        else:
            return '[Node:{}]'.format(self._label)
 
class LRBTree:
    def __init__(self, root):
        self._root = root
        self._nodes = {}
        self._leaves = []

        def traverse(r):
            children = r.children()
            if len(children) == 0:
                self._leaves.append(r)
            if r.label() is not None:
                self._nodes[r.label()] = r
            for c in children:
                traverse(c)
            return None
        
        traverse(root)
        
        return None
    
    def node(self, label):
        return self._nodes[label]
    
    def node_dict(self):
        return self._nodes.copy()
    
    def root(self):
        return self._root
    
    def leaves(self):
        return self._leaves.copy()
    
    def subtree(self, label):
        return LRBTree(self.node(label))
    
def linkage_to_tree(Z, labels):
    n = len(labels)
    leaves = [Node(label = lbl) for lbl in labels]
    nonleaves = []
    for k, r in enumerate(Z):
        i = int(r[0])
        j = int(r[1])
        if i < n:
            c1 = leaves[i]
        else:
            c1 = nonleaves[i - n]
        if r[1] < n:
            c2 = leaves[j]
        else:
            c2 = nonleaves[j - n]
            
        nonleaves.append(Node(c1, c2, label = k + n))
    
    return LRBTree(nonleaves[-1])

# find indices of maximal sublinkage of Z0 that embeds into Z1
def max_sublinkage(Z0, Z1, labels):
    n = len(labels)
    T1 = linkage_to_tree(Z1, labels)
    agree = []
    disagree = []
    nonleaves = {}
    for i, r in enumerate(Z0):
        j = int(r[0])
        k = int(r[1])
        
        if j in disagree or k in disagree:
            disagree.append(i + n)
            continue
        
        if j < n:
            nd1 = T1.node(labels[j])
        else:
            nd1 = nonleaves[j]
        if k < n:
            nd2 = T1.node(labels[k])
        else:
            nd2 = nonleaves[k]
            
        if nd1.parent() == nd2.parent():
            agree.append(i + n)
            nonleaves[i + n] = nd1.parent()
        else:
            disagree.append(i + n)
            
    return [j - n for j in agree]

# find maximal sublinkage of Z achieving a specified level of consensus among
# bootstrap replicates
def consensus(Z, Z_boot, labels, p):
    counts = np.zeros(len(Z))
    for Z1 in Z_boot:
        for i in max_sublinkage(Z, Z1, labels):
            counts[i] += 1
            
    b = len(Z_boot)
    return [i for i in range(len(Z)) if counts[i] >= p * b]
        
# find the subtree of T generated by a set of leaf nodes
def subtree_from_leaves(T, leaves):
    _leaves = set(leaves)
    T_sub = LRBTree(_leaves.pop())
    while len(_leaves) > 0:
        T_sub = LRBTree(T_sub.root().parent())
        _leaves -= set(T_sub.leaves())
        
    return T_sub

def sublinkage_from_leaves(Z, labels, leaves):
    T = linkage_to_tree(Z, labels)
    lf_nds = [T.node(lf) for lf in leaves]
    T_sub = subtree_from_leaves(T, lf_nds)
    sub_inds = [i - len(labels) for i, nd in T_sub.node_dict().items()
                if nd not in T_sub.leaves()]
    return split_linkage(Z, labels, sub_inds)

def child_leaves(nd):
    return [LRBTree(c).leaves() for c in nd.children()]

# checks for agreement between Z0 and Z1 of each isolated merging of clusters
def merge_agreement(Z0, Z1, labels):
    n = len(labels)
    T0 = linkage_to_tree(Z0, labels)
    T1 = linkage_to_tree(Z1, labels)
    agree = np.zeros(len(Z0), dtype = bool)
    
    for i in range(len(agree)):
        nd0 = T0.node(n + i)
        L0 = child_leaves(nd0)
        g1 = [T1.node(lf.label()) for lf in L0[0] + L0[1]]
        S1 = subtree_from_leaves(T1, g1)
        L1 = child_leaves(S1.root())
        
        lf00 = frozenset(lf.label() for lf in L0[0])
        lf01 = frozenset(lf.label() for lf in L0[1])
        lf10 = frozenset(lf.label() for lf in L1[0])
        lf11 = frozenset(lf.label() for lf in L1[1])
        agree[i] = (set([lf00, lf01]) == set([lf10, lf11]))
        
    return agree

# determines the consensus among bootstrap replicates on each isolated
# merging of clusters as a proportion
def merge_consensus(Z0, Z_boot, labels):
    counts = np.zeros(len(Z0))
    for Z1 in Z_boot:
        counts += merge_agreement(Z0, Z1, labels)
        
    return counts / len(Z_boot)

# checks if each flat cluster in Z0 is also in Z1
def flat_agreement(Z0, Z1, labels):
    n = len(labels)
    T0 = linkage_to_tree(Z0, labels)
    T1 = linkage_to_tree(Z1, labels)
    agree = np.zeros(len(Z0), dtype = bool)
    
    for i in range(len(agree)):
        nd0 = T0.node(n + i)
        L0 = LRBTree(nd0).leaves()
        g1 = [T1.node(lf.label()) for lf in L0]
        S1 = subtree_from_leaves(T1, g1)
        L1 = S1.leaves()
        L10 = [T0.node(lf.label()) for lf in L1]
        
        agree[i] = (set(L0) == set(L10))
        
    return agree

# determines the consensus among bootstrap replicates on each flat cluster as
# a proportion
def flat_consensus(Z0, Z_boot, labels):
    counts = np.zeros(len(Z0))
    for Z1 in Z_boot:
        counts += flat_agreement(Z0, Z1, labels)
        
    return counts / len(Z_boot)

# performs hierarchical clustering and measure bootstrap consensus. The
# output is an (n-1) x 5 array, where n is the number of leaves. The first
# 4 columns is a scipy.cluster.hierarchy style linkage matrix. The 5th
# column contains consensus proportions.
def consensus_cluster(D, labels, method = 'average',
                      consensus = flat_consensus, metric = False,
                      optimal_ordering = False):
    Z_all = []
    if metric:
        for dist in D:
            Z_all.append(sch.linkage(dist, method = method,
                                     optimal_ordering = optimal_ordering))
    else:
        for dist in D:
            W = (sch.linkage(1 - dist, method = method,
                             optimal_ordering = optimal_ordering))
            W[:, 2] = 1 - W[:, 2]
            Z_all.append(W)
    Z_all = np.array(Z_all)
    
    cons = consensus(Z_all[0], Z_all[1:], labels)
    Z = np.zeros((len(Z_all[0]), 5))
    Z[:, :4] = Z_all[0]
    Z[:, 4] = cons
    return Z