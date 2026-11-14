"""Even-by-even standard Cram: limited-search first vs 180-degree mirror second."""
import argparse,csv,hashlib,random,signal,time
from pathlib import Path
from pfair.rules import Rules,Variant
from pfair.players import Player,EVALS,wilson

class Timeout(Exception): pass
def alarm_handler(*_): raise Timeout()

def rotate(mask,width,height):
    result=0
    for i in range(width*height):
        if mask & (1<<i):
            row,col=divmod(i,width)
            result |= 1 << ((height-1-row)*width+(width-1-col))
    return result

def game(rules,depth,rng):
    v=rules.variant
    if v.partisan or v.memory!='off' or v.pie or v.shapes!=('domino',) or v.width%2 or v.height%2:
        raise ValueError('Only standard even-by-even Cram without pie or memory')
    first=Player(rules,depth,EVALS['zero'],rng);state=rules.initial_state(); plies=0;mirror_replies=0
    while True:
        if not rules.successors(state): return {'first_wins':False,'plies':plies,'mirror_replies':mirror_replies}
        before=state[0];state=first.choose(state);plies+=1
        if not rules.successors(state): return {'first_wins':True,'plies':plies,'mirror_replies':mirror_replies}
        played=state[0]^before;target=rotate(played,v.width,v.height)
        legal=[next_state for (_,mask),next_state in rules.successors(state) if mask==target]
        if len(legal)!=1: raise AssertionError('Mirror move was not uniquely legal')
        state=legal[0];plies+=1;mirror_replies+=1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--games',type=int,default=1000);ap.add_argument('--sizes',default='4,6');ap.add_argument('--depths',default='1,2');ap.add_argument('--seed',type=int,default=20261113);ap.add_argument('--timeout',type=int,default=10);ap.add_argument('--out',default='mirror_experiment/matches.csv');a=ap.parse_args()
    signal.signal(signal.SIGALRM,alarm_handler);fields=['size','game','first_policy','second_policy','depth','evaluation','pie','memory','match_index','seed','first_wins','plies','mirror_replies','seconds','status']
    with open(a.out,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for size in map(int,a.sizes.split(',')):
            rules=Rules(Variant(size,size))
            for depth in map(int,a.depths.split(',')):
                wins=done=0;start=time.perf_counter()
                for i in range(a.games):
                    seed=int.from_bytes(hashlib.sha256(f'{a.seed}:{i}'.encode()).digest()[:8],'big');rng=random.Random(seed);t=time.perf_counter();g=None;status='ok'
                    try:
                        signal.alarm(a.timeout);g=game(rules,depth,rng)
                    except Timeout:status='timeout'
                    except Exception as exc:status=f'error:{type(exc).__name__}:{exc}'
                    finally:signal.alarm(0)
                    sec=time.perf_counter()-t
                    if g:done+=1;wins+=g['first_wins']
                    w.writerow(dict(size=size,game='cram',first_policy='depth_limited_alpha_beta',second_policy='rotate_180',depth=depth,evaluation='zero',pie=False,memory='off',match_index=i,seed=seed,first_wins=int(g['first_wins']) if g else '',plies=g['plies'] if g else '',mirror_replies=g['mirror_replies'] if g else '',seconds=f'{sec:.8f}',status=status));f.flush()
                print(f'{size}x{size} depth={depth}: first wins {wins}/{done}, ci={wilson(wins,done)}, seconds={time.perf_counter()-start:.2f}',flush=True)
if __name__=='__main__': main()
