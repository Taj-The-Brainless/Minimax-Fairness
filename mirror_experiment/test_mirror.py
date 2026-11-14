import random
import pytest
from pfair.rules import Rules,Variant
from mirror_experiment.run_mirror import rotate,game

@pytest.mark.parametrize('n',[2,4,6])
def test_rotated_placements_legal_and_not_fixed(n):
    rules=Rules(Variant(n,n))
    placements=rules.placements[0][0]
    for m in placements:
        assert rotate(rotate(m,n,n),n,n)==m
        assert rotate(m,n,n) in placements
        assert not (rotate(m,n,n)&m)

@pytest.mark.parametrize('n',[2,4,6])
@pytest.mark.parametrize('depth',[1,2])
def test_mirror_wins_sample_games(n,depth):
    for seed in range(10):
        result=game(Rules(Variant(n,n)),depth,random.Random(seed))
        assert not result['first_wins']
        assert result['plies']==2*result['mirror_replies']

def test_rejects_unsupported_rules():
    with pytest.raises(ValueError): game(Rules(Variant(5,5)),1,random.Random(0))
    with pytest.raises(ValueError): game(Rules(Variant(4,4,partisan=True)),1,random.Random(0))
