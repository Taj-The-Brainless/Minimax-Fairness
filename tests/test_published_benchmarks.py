"""Published normal-play outcomes; dimensions in these cases are rows, columns.
Cram: Uiterwijk 2020, doi:10.1007/978-3-030-65883-0_8, Theorems 1–2.
Domineering: Lachmann, Moore and Rapaport 2002, Figure 1, pp. 312.
"""
import pytest
from pfair.rules import Variant
from pfair.solver import solve_variant

CASES = [
 ('cram',2,2,False),('cram',2,4,False),('cram',4,4,False),
 ('cram',2,3,True),('cram',3,2,True),('cram',3,4,True),
 ('domineering',2,2,True),('domineering',2,3,True),('domineering',2,4,False),
 ('domineering',2,5,True),('domineering',3,3,True),('domineering',3,4,False),
 ('domineering',4,3,True),('domineering',4,4,True),('domineering',5,5,False)]

@pytest.mark.parametrize('game,rows,columns,expected', CASES)
def test_published_outcome(game,rows,columns,expected):
    v=Variant(width=columns,height=rows,partisan=game=='domineering',first_orientation='v')
    r=solve_variant(v,node_limit=2_000_000,use_tt=True)
    assert r.solved, f'node limit exceeded for {game} {rows}x{columns}'
    assert r.first_wins == expected
