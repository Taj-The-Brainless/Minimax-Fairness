"""Independent-seed practical matches using the project's unchanged players."""
import argparse,csv,hashlib,random,signal,time
from pathlib import Path
from pfair.rules import Rules,Variant
from pfair.players import EVALS,Player,play_game

class Deadline(Exception): pass
def timed_out(*args): raise Deadline()

def main():
 p=argparse.ArgumentParser();p.add_argument('--games',type=int,required=True);p.add_argument('--sizes',default='4,5,6,7,8');p.add_argument('--depths',default='1,2');p.add_argument('--seed',type=int,default=20261113);p.add_argument('--timeout',type=int,default=10);p.add_argument('--out',required=True);a=p.parse_args()
 signal.signal(signal.SIGALRM,timed_out)
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
 fields=['game','width','height','shapes','partisan','pie','memory','depth','evaluation','random_opening','base_seed','match_index','match_seed','first_seat','first_wins','side0_wins','plies','swapped','seconds','status']
 with out.open('w',newline='') as f:
  wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader()
  for size in map(int,a.sizes.split(',')):
   for game in ('cram','domineering'):
    for depth in map(int,a.depths.split(',')):
     rules=Rules(Variant(size,size,partisan=(game=='domineering'))); evaluation='mobility' if game=='domineering' else 'zero'
     start=time.perf_counter();wins=finished=0
     for i in range(a.games):
      seed=int.from_bytes(hashlib.sha256(f'{a.seed}:{i}'.encode()).digest()[:8],'big')
      rng=random.Random(seed); players=[Player(rules,depth,EVALS[evaluation],rng),Player(rules,depth,EVALS[evaluation],rng)]
      # Agents have identical policies. Alternating labels controls identity, not orientation.
      first_seat='A' if i%2==0 else 'B'
      if first_seat=='B': players.reverse()
      t=time.perf_counter();g=None;status='ok'
      try:
       signal.alarm(a.timeout);g=play_game(rules,players,rng,random_opening=0)
      except Deadline: status='timeout'
      except Exception as e: status='error:'+type(e).__name__
      finally: signal.alarm(0)
      seconds=time.perf_counter()-t
      if g: wins+=g['seat_a_wins'];finished+=1
      row=dict(game=game,width=size,height=size,shapes='domino',partisan=rules.variant.partisan,pie=False,memory='off',depth=depth,evaluation=evaluation,random_opening=0,base_seed=a.seed,match_index=i,match_seed=seed,first_seat=first_seat,first_wins=int(g['seat_a_wins']) if g else '',side0_wins=int(g['side0_wins']) if g else '',plies=g['plies'] if g else '',swapped=int(g['swapped']) if g else '',seconds=f'{seconds:.8f}',status=status)
      wr.writerow(row);f.flush()
     print(f'{size}x{size} {game} depth={depth}: {wins}/{finished} time={time.perf_counter()-start:.2f}s',flush=True)
if __name__=='__main__': main()
