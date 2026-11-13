import csv,math,statistics
from collections import defaultdict,Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pfair.players import wilson

root=Path('fairness_experiment'); inp=list(csv.DictReader((root/'main_matches.csv').open()));pilot=list(csv.DictReader((root/'pilot.csv').open()))
exact={r['variant_id']:r for r in csv.DictReader((root/'previous_main/exact.csv').open())}
ds={(r['variant_id'],r['eval']):r for r in csv.DictReader((root/'previous_main/dstar.csv').open())}
groups=defaultdict(list)
for r in inp: groups[(r['game'],int(r['width']),int(r['depth']),r['evaluation'])].append(r)
out=[]
for (game,size,depth,ev),rows in sorted(groups.items()):
 ok=[r for r in rows if r['status']=='ok'];n=len(ok);k=sum(int(r['first_wins']) for r in ok);lo,hi=wilson(k,n) if n else (float('nan'),float('nan'))
 v=f"{size}x{size}_domino_{'impartial' if game=='cram' else 'partisan-v'}"; ex=exact.get(v,{}); d=ds.get((v,ev),{})
 classification='supports_near_fair' if lo>=.45 and hi<=.55 else ('outside_range' if hi<.45 or lo>.55 else 'inconclusive')
 out.append(dict(game=game,size=size,depth=depth,evaluation=ev,requested=len(rows),n=n,wins=k,rate=k/n if n else '',ci_low=lo,ci_high=hi,distance=abs(k/n-.5) if n else '',classification=classification,mean_seconds=statistics.mean(float(r['seconds']) for r in ok) if n else '',mean_plies=statistics.mean(int(r['plies']) for r in ok) if n else '',failures=len(rows)-n,exact_winner=ex.get('winner','not_available'),exact_nodes=ex.get('nodes',''),dstar=d.get('d_star',''),dstar_status=d.get('status','not_available')))
with (root/'summary.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=out[0]);w.writeheader();w.writerows(out)
with (root/'pilot_summary.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['game','size','depth','n','wins','mean_seconds','mean_plies','failures'])
 for key in sorted({(r['game'],int(r['width']),int(r['depth'])) for r in pilot}):
  rr=[r for r in pilot if (r['game'],int(r['width']),int(r['depth']))==key];good=[r for r in rr if r['status']=='ok'];w.writerow([*key,len(good),sum(int(r['first_wins']) for r in good),statistics.mean(float(r['seconds']) for r in good),statistics.mean(int(r['plies']) for r in good),len(rr)-len(good)])
plot=root/'plots';plot.mkdir(exist_ok=True)
fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
for ax,game in zip(axes,['cram','domineering']):
 for depth in (1,2):
  rows=sorted([r for r in out if r['game']==game and r['depth']==depth],key=lambda r:r['size']);x=[r['size'] for r in rows];y=[r['rate'] for r in rows];ax.errorbar(x,y,yerr=[[r['rate']-r['ci_low'] for r in rows],[r['ci_high']-r['rate'] for r in rows]],marker='o',capsize=3,label=f'depth {depth} (n=200; 6×6: 1000)')
 ax.axhspan(.45,.55,color='grey',alpha=.13);ax.axhline(.5,color='black',linestyle='--',lw=1);ax.set_title(game+' | '+('zero' if game=='cram' else 'mobility'));ax.set_xlabel('Board width = height');ax.set_xticks([4,5,6,7,8]);ax.legend(fontsize=8)
axes[0].set_ylabel('First-seat win rate (95% Wilson CI)');fig.tight_layout();fig.savefig(plot/'win_rate_by_size.png',dpi=150);plt.close(fig)
fig,ax=plt.subplots(figsize=(7,4))
for game in ('cram','domineering'):
 for depth in (1,2):
  rows=sorted([r for r in out if r['game']==game and r['depth']==depth],key=lambda r:r['size']);ax.plot([r['size'] for r in rows],[r['mean_seconds'] for r in rows],marker='o',label=f'{game}, depth {depth}')
ax.set(xlabel='Board width = height',ylabel='Mean match duration (seconds)',title='Runtime: n=200; 6×6: n=1000');ax.legend();fig.tight_layout();fig.savefig(plot/'runtime_by_size.png',dpi=150);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
for ax,depth in zip(axes,(1,2)):
 for game in ('cram','domineering'):
  rows=sorted([r for r in out if r['game']==game and r['depth']==depth],key=lambda r:r['size']);ax.errorbar([r['size'] for r in rows],[r['rate'] for r in rows],yerr=[[r['rate']-r['ci_low'] for r in rows],[r['ci_high']-r['rate'] for r in rows]],marker='o',capsize=2,label=game+' / '+rows[0]['evaluation'])
 ax.axhline(.5,color='black',linestyle='--',lw=1);ax.set(title=f'Depth {depth}, n=200; 6×6: 1000',xlabel='Board width = height');ax.legend(fontsize=8)
axes[0].set_ylabel('First-seat win rate (95% Wilson CI)');fig.tight_layout();fig.savefig(plot/'rule_comparison.png',dpi=150);plt.close(fig)
fig,ax=plt.subplots(figsize=(7,5))
for game,marker in [('cram','o'),('domineering','s')]:
 for r in out:
  if r['game']==game and r['depth']==2 and r['exact_winner'] in ('first','second'):
   ax.scatter(int(r['exact_nodes']),r['distance'],marker=marker,label=game if not any(t.get_text()==game for t in ax.get_legend_handles_labels()[1] if hasattr(t,'get_text')) else None)
   ax.annotate(f"{game} {r['size']}×{r['size']}",(int(r['exact_nodes']),r['distance']),xytext=(4,3),textcoords='offset points',fontsize=7)
ax.set_xscale('log');ax.set(xlabel='Exact solver nodes (previous run, no pie)',ylabel='Distance of first-seat win rate from 0.50',title='Known exact cases only; depth 2, n=200');fig.tight_layout();fig.savefig(plot/'exact_nodes_vs_fairness.png',dpi=150);plt.close(fig)
print('summary rows',len(out),'matches',len(inp),'statuses',dict(Counter(r['status'] for r in inp)))
