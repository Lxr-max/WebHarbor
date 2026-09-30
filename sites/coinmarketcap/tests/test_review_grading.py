"""Natural watchlist summaries retain entity, price and percentage checks."""
import importlib.util
import json
from pathlib import Path

import pytest

VERIFY = Path(__file__).resolve().parents[1] / 'verify'
spec = importlib.util.spec_from_file_location('review_contract', VERIFY / 'contract_engine.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
CONTRACT = json.loads((VERIFY / 'contract.json').read_text())


@pytest.mark.parametrize('task, index, answer', [
    (7, 2, 'Bitcoin — price is $83,622.87, 24-hour change +0.12%'),
    (21, 4, 'XRP — price is $1.49, 24-hour change -0.41%'),
])
def test_natural_watchlist_claims(task, index, answer):
    claim = [CONTRACT[f'CoinMarketCap--{task}']['claims'][index]]
    engine.check_claims(answer, claim)
    engine.check_claims(answer.replace('price is', 'price').upper(), claim)
    with pytest.raises(ValueError):
        engine.check_claims(answer.replace('$83,622.87', '$83,000').replace('$1.49', '$1.50'), claim)
    with pytest.raises(ValueError):
        engine.check_claims(answer.replace('$', '€'), claim)
    with pytest.raises(ValueError):
        engine.check_claims('The following is false: ' + answer, claim)
