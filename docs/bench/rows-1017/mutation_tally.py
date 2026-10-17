import json, re, sys
"""Tally a filtered held-out re-run. Usage: mutation_tally.py <dir with results.json, classification.json, manifest.json>
(the held-out set lives in bench-local/mutation/heldout, outside the repo; results.json here is the filtered re-run)."""
H = sys.argv[1].rstrip('/') + '/'
res = json.load(open(H + 'results.json'))
cls = json.load(open(H + 'classification.json'))
man = json.load(open(H + 'manifest.json'))
vac = [k for k, v in man.items() if v['label'] == 'vacuous']
gen = [k for k, v in man.items() if v['label'] == 'genuine']
def lines(k, tag):
    return [l for l in res[k].splitlines() if l.startswith(tag)]
def has(k, line, new, tags):
    return any(re.match(rf'(?:{tags}) \S+:{line}: .*-> .*{re.escape(new.strip())}', l) or (l.split(':', 2)[1] == str(line) and new.strip() in l)
               for t in tags.split('|') for l in lines(k, t))
fl = lambda k: bool(lines(k, 'SURVIVED') or lines(k, 'NOT_COVERED'))
hit = [k for k in vac if fl(k)]
print('vacuous flagged', len(hit), '/', len(vac), 'misses', sorted(set(vac) - set(hit)))
eq_flag = [c for c in gen if any(m['kind'] == 'EQUIVALENT' and has(c, m['line'], m['new'], 'SURVIVED') for m in cls.get(c, []))]
print('genuine with >=1 equivalent still SURVIVED', len(eq_flag), eq_flag)
eq_total = sum(m['kind'] == 'EQUIVALENT' for c in gen for m in cls.get(c, []))
eq_dem = sum(m['kind'] == 'EQUIVALENT' and has(c, m['line'], m['new'], 'LIKELY_EQUIVALENT') for c in gen for m in cls.get(c, []))
thin_total = sum(m['kind'] == 'THIN' for c in gen for m in cls.get(c, []))
thin_dem = [(c, m['line'], m['new']) for c in gen for m in cls.get(c, []) if m['kind'] == 'THIN' and has(c, m['line'], m['new'], 'LIKELY_EQUIVALENT')]
thin_surv = sum(m['kind'] == 'THIN' and has(c, m['line'], m['new'], 'SURVIVED') for c in gen for m in cls.get(c, []))
print('equivalent mutants', eq_total, 'demoted', eq_dem)
print('thin mutants', thin_total, 'still SURVIVED', thin_surv, 'wrongly demoted', thin_dem)
print('vacuous mutants demoted (LIKELY_EQUIVALENT lines on vacuous cases):', [(k, l) for k in vac for l in lines(k, 'LIKELY_EQUIVALENT')])
print('all LIKELY_EQUIVALENT lines:')
for k in man:
    for l in lines(k, 'LIKELY_EQUIVALENT') if k in res else []:
        print(' ', k, man[k]['label'], l)
print('genuine clean OK', [c for c in gen if c in res and not fl(c)])
