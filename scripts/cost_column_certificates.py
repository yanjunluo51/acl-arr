"""Complete-subset weighted column witnesses for the frozen median model."""
import numpy as np
from numba import njit
from column_certificate import support_masks, certify_subset


def price_profiles(T):
    # All profiles have identical total/mean price. These are declared cost
    # sensitivities indexed by frozen candidate identity, not hardware timings.
    return np.array([[2*T-1]*T,[T+2*r for r in range(T)],
                     [T+2*r for r in reversed(range(T))]],dtype=np.int64)


@njit(cache=True)
def _capacity(hist,offset,b):
    count=0
    for value in range(len(hist)):
        price=value+offset
        take=hist[value] if price==0 else min(hist[value],b//price)
        count+=take;b-=take*price
        if take<hist[value]:break
    return count


@njit(cache=True)
def _scan(supports,freq,T,b,prices,eps,lower_counts,initial_masks):
    size=1<<T;pc=np.zeros(size,np.int64)
    paid=np.zeros((len(prices),size),np.int64)
    best=np.zeros((len(eps),len(prices)),np.int64)
    masks=np.zeros_like(best);counts=np.zeros_like(best)
    for subset in range(1,size):
        bit=subset&(-subset);j=0
        while (1<<j)!=bit:j+=1
        previous=subset^bit;pc[subset]=pc[previous]+1
        for p in range(len(prices)):paid[p,subset]=paid[p,previous]+prices[p,j]
    for t in range(len(eps)):
        for p in range(len(prices)):
            masks[t,p]=initial_masks[t];best[t,p]=paid[p,initial_masks[t]]
            counts[t,p]=pc[initial_masks[t]]
    evaluated=0
    for subset in range(size):
        useful=False
        for t in range(len(eps)):
            if pc[subset]<lower_counts[t]:continue
            for p in range(len(prices)):
                if paid[p,subset]<best[t,p] or (paid[p,subset]==best[t,p] and pc[subset]<counts[t,p]):useful=True
        if not useful:continue
        hist=np.zeros(T+1,np.int64)
        for row in range(len(supports)):hist[pc[supports[row]&subset]]+=freq[row]
        vminus=_capacity(hist,T-pc[subset],b);vplus=_capacity(hist,0,b)
        evaluated+=1
        for t in range(len(eps)):
            if vplus-vminus>eps[t]:continue
            for p in range(len(prices)):
                if paid[p,subset]<best[t,p] or (paid[p,subset]==best[t,p] and pc[subset]<counts[t,p]):
                    best[t,p]=paid[p,subset];masks[t,p]=subset;counts[t,p]=pc[subset]
    return best,masks,counts,evaluated


@njit(cache=True)
def _audit_raw_rows(raw,T,b,prices,eps,best):
    # Separate representation, raw rows, all cheaper action sets. In particular
    # do not use the histogram compressor or entry-derived lower-count pruning.
    size=1<<T;pc=np.zeros(size,np.int64)
    for subset in range(1,size):pc[subset]=pc[subset>>1]+(subset&1)
    checked=0
    for subset in range(size):
        cost=np.zeros(len(prices),np.int64)
        for j in range(T):
            if subset>>j&1:
                for p in range(len(prices)):cost[p]+=prices[p,j]
        relevant=False
        for t in range(len(eps)):
            for p in range(len(prices)):
                if cost[p]<best[t,p]:relevant=True
        if not relevant:continue
        lower=np.empty(len(raw),np.int64)
        for row in range(len(raw)):
            # Count agreement bits instead of opposition-support frequencies.
            agreements=pc[(~raw[row])&subset]
            lower[row]=pc[subset]-agreements
        lower.sort();s=0;vminus=0;vplus=0
        for row in range(len(lower)):
            s+=lower[row]
            if s<=b:vplus+=1
        s=0
        for row in range(len(lower)):
            s+=lower[row]+T-pc[subset]
            if s<=b:vminus+=1
        checked+=1
        for t in range(len(eps)):
            if vplus-vminus<=eps[t]:
                for p in range(len(prices)):
                    if cost[p]<best[t,p]:return False,checked
    return True,checked


def minimum_cost_columns(bits,budget,epsilon,entry_bounds,initial_mask):
    y=np.asarray(bits,dtype=np.int64);m,T=y.shape
    prices=price_profiles(T);eps=np.asarray([0,epsilon],dtype=np.int64)
    raw=support_masks(y);supports,freq=np.unique(raw,return_counts=True)
    lower=np.asarray([(q+m-1)//m if m else 0 for q in entry_bounds],dtype=np.int64)
    initial=np.asarray([initial_mask,initial_mask],dtype=np.int64)
    best,masks,counts,evaluated=_scan(supports,freq,T,budget,prices,eps,lower,initial)
    for t in range(2):
        for p in range(3):
            lo,hi=certify_subset(y,budget,int(masks[t,p]));assert hi-lo<=eps[t]
            assert sum(prices[p,j] for j in range(T) if int(masks[t,p])>>j&1)==best[t,p]
    valid,audited=_audit_raw_rows(raw,T,budget,prices,eps,best)
    assert valid,'A cheaper column certificate exists'
    return {'prices':prices.tolist(),'minimum_costs':best.tolist(),'subset_masks':masks.tolist(),
            'column_counts':counts.tolist(),'subsets_evaluated':int(evaluated),
            'cheaper_subsets_independently_checked':int(audited)}
