from pathlib import Path
import json
import sys
import pytest
V = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V))
from contract_engine import check_claims, matches
SPECS = json.loads((V / 'contract.json').read_text())
CASES = json.loads((V / 'tests/answer_controls.json').read_text())

@pytest.mark.parametrize('case', CASES, ids=[c['task']+' '+c['name'] for c in CASES])
def test_declared_answer_polarity(case):
    if case['expected']:
        check_claims(case['answer'], SPECS[case['task']]['claims'])
    else:
        with pytest.raises(ValueError):
            check_claims(case['answer'], SPECS[case['task']]['claims'])

def test_real_signup_password_with_fresh_salts():
    import bcrypt
    password = 'ReviewPassword42!'
    for _ in range(2):
        value = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
        assert matches(value, {'bcrypt_password': password})
        assert not matches(value, {'bcrypt_password': 'different-password'})
