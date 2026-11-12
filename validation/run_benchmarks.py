"""Published Cram parity theorems and Domineering outcome classes; rows x columns."""
import csv, multiprocessing as mp, time
from pathlib import Path
from pfair.rules import Variant
from pfair.solver import solve_variant
from pfair.reference import reference_first_wins

# source identifier, game, rows, columns, published winner (vertical starts for Domineering)
CASES = [
 ('U2020-T1','Cram',2,2,'second'),('U2020-T1','Cram',2,4,'second'),('U2020-T1','Cram',4,4,'second'),
 ('U2020-T2','Cram',2,3,'first'),('U2020-T2','Cram',3,2,'first'),('U2020-T2','Cram',3,4,'first'),
 ('L2002','Domineering',2,2,'first'),('L2002','Domineering',2,3,'first'),('L2002','Domineering',2,4,'second'),
 ('L2002','Domineering',2,5,'first'),('L2002','Domineering',3,3,'first'),('L2002','Domineering',3,4,'second'),
 ('L2002','Domineering',4,3,'first'),('L2002','Domineering',4,4,'first'),('L2002','Domineering',5,5,'second')]
LIMIT=2_000_000
TIMEOUT=10

def work(conn, game, rows, cols, mode):
    v=Variant(width=cols,height=rows,partisan=game=='Domineering',first_orientation='v')
    start=time.perf_counter()
    if mode=='exact':
        r=solve_variant(v,node_limit=LIMIT,use_tt=True)
        out={'winner':('first' if r.first_wins else 'second') if r.solved else '', 'nodes':r.nodes,'seconds':r.seconds,'solved':r.solved}
    else:
        w=reference_first_wins(v)
        out={'winner':'first' if w else 'second','seconds':time.perf_counter()-start}
    conn.send(out); conn.close()

def bounded(game,rows,cols,mode):
    recv,send=mp.Pipe(False)
    proc=mp.Process(target=work,args=(send,game,rows,cols,mode)); proc.start(); send.close()
    proc.join(TIMEOUT)
    if proc.is_alive(): proc.terminate(); proc.join(); recv.close(); return {'status':'timeout'}
    result=recv.recv() if recv.poll() else {'status':f'error_exit_{proc.exitcode}'}
    recv.close(); return result

def main():
    results=[]
    for source,game,rows,cols,published in CASES:
        exact=bounded(game,rows,cols,'exact')
        ref=bounded(game,rows,cols,'reference') if rows*cols<=12 else {'status':'not_run_size'}
        status=('INCONCLUSIVE' if not exact.get('solved') else 'PASS' if exact['winner']==published and (not ref.get('winner') or ref['winner']==published) else 'FAIL')
        row=dict(source=source,game=game,rows=rows,columns=cols,published=published,exact=exact.get('winner',''),reference=ref.get('winner',ref.get('status','')),nodes=exact.get('nodes',''),seconds=exact.get('seconds',''),reference_seconds=ref.get('seconds',''),solved=exact.get('solved',False),exact_status=exact.get('status','completed' if exact.get('solved') else 'node_limit'),result=status)
        results.append(row); print(row,flush=True)
    with open(Path(__file__).parent/'benchmark_results.csv','w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=results[0]);writer.writeheader();writer.writerows(results)
if __name__=='__main__': main()
