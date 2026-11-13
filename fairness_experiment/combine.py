import csv
from pathlib import Path
p=Path('fairness_experiment')
a=list(csv.DictReader((p/'main_200.csv').open())); b=list(csv.DictReader((p/'main_6x6_1000.csv').open()))
old=[r for r in a if r['width']=='6']; subset=[r for r in b if int(r['match_index'])<200]
key=lambda r:(r['game'],r['depth'],int(r['match_index']))
assert len(old)==len(subset)==800
for x,y in zip(sorted(old,key=key),sorted(subset,key=key)):
 assert all(x[k]==y[k] for k in x if k!='seconds')
rows=[r for r in a if r['width']!='6']+b
with (p/'main_matches.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=a[0]);w.writeheader();w.writerows(rows)
print('combined',len(rows),'rows; repeated 6x6 games match except timing')
