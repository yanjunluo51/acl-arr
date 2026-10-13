"""Exact offline positive-gap witnesses in the median completion model.

Epsilon counts boundary outputs; selected interior outputs cancel from the gap.
This characterizes hindsight entry certificates, not online query discovery.
"""
import bisect


def minimum_gap_certificate(row_sums, candidates, budget, epsilon):
    z = sorted(int(x) for x in row_sums)
    T, b, e = int(candidates), int(budget), int(epsilon)
    if T < 1 or b < 0 or e < 0 or any(x < 0 or x > T for x in z):
        raise ValueError('Invalid median certificate instance')
    m = len(z)
    pref = [0]
    for x in z:
        pref.append(pref[-1] + x)
    optimum = bisect.bisect_right(pref, b) - 1
    best = None
    for L in range(max(0, optimum - e), optimum + 1):
        safe = max(0, L*T - b)
        p = L + e + 1
        exclusion = level = 0
        if p <= m:
            # Sum of the p smallest true costs capped at level t.
            left, right = 0, T
            while left < right:
                t = (left + right) // 2
                j = min(p, bisect.bisect_right(z, t))
                capped = pref[j] + (p-j)*t
                if capped >= b+1:
                    right = t
                else:
                    left = t+1
            level = left
            j = min(p, bisect.bisect_right(z, level))
            assert pref[j] + (p-j)*level >= b+1
            exclusion = b+1 + (m-p)*level
        result = {'queries': safe+exclusion, 'safe_target': L,
                  'exclusion_target': p, 'agreements': safe,
                  'oppositions': exclusion, 'cap_level': level,
                  'true_boundary_optimum': optimum}
        if best is None or result['queries'] < best['queries']:
            best = result
    assert best is not None
    return best
