"""Arithmetic acceleration only; strict IEEE left-to-right sums, no fast math."""
import numpy as np
from numba import njit

@njit(cache=True,fastmath=False)
def capacities(hist,budgets):
    result=np.empty(len(budgets),dtype=np.int64)
    for j in range(len(budgets)):
        remain=int(budgets[j]);count=int(hist[0])
        for value in range(1,len(hist)):
            take=min(int(hist[value]),remain//value)
            count+=take;remain-=take*value
            if take<hist[value]:break
        result[j]=count
    return result

@njit(cache=True,fastmath=False)
def mean_flips(base,score,threshold):
    M=len(base);value=0.
    for j in range(M):value=value+base[j]
    old=value/M>=threshold;n=0
    for member in range(M):
        value=0.
        for j in range(M):value=value+(score if j==member else base[j])
        n+=((value/M>=threshold)!=old)
    return n
