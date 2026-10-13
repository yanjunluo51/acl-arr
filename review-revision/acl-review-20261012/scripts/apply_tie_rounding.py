"""Final rendering layer: decimal half-up for exact ties printed by float formatting.

Several earlier renderers formatted float means with Python's binary rounding,
which sends exact ties such as 1289.55 = 51582/40 to the lower neighbour.
Appendix B states decimal half-up rounding. Each correction stores the exact
rational value; this script checks it, then rewrites only that cell. Running it
again leaves the tables unchanged.
"""
import json
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]


def halfup(q, digits):
    v = Decimal(q.numerator) / Decimal(q.denominator)
    return str(v.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def main(check_only=False):
    fixes = json.load((EXP/'outputs/tie_rounding_corrections.json').open())
    by = {}
    for f in fixes:
        digits = len(f['half_up'].split('.')[1])
        assert halfup(Fraction(f['exact_value']), digits) == f['half_up'], f
        by.setdefault(f['table'], []).append(f)
    pending = 0
    for table, items in by.items():
        path = ROOT/'manuscript/tables'/table
        lines = path.read_text().split('\n')
        for f in items:
            fixed = {g['column_index']: g['half_up'] for g in items if g['row_cells'] == f['row_cells']}
            rows = []
            for i, line in enumerate(lines):
                cells = [c.strip() for c in line.split('\\\\')[0].split('&')]
                if len(cells) == len(f['row_cells']) and all(
                        c == r or fixed.get(j) == c for j, (c, r) in enumerate(zip(cells, f['row_cells']))):
                    rows.append(i)
            assert len(rows) == 1, (table, f['row_cells'], rows)
            body, sep, tail = lines[rows[0]].partition('\\\\')
            parts = body.split('&')
            cell = parts[f['column_index']].strip()
            assert cell in (f['printed'], f['half_up']), (table, cell)
            if cell == f['printed']:
                pending += 1
                parts[f['column_index']] = parts[f['column_index']].replace(f['printed'], f['half_up'])
                lines[rows[0]] = '&'.join(parts) + sep + tail
        if not check_only:
            path.write_text('\n'.join(lines))
    return len(fixes), pending


if __name__ == '__main__':
    total, pending = main()
    print(f'{total} corrections, {pending} applied now')
