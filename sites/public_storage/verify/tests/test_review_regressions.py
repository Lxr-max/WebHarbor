"""Reject entity swaps and plausible-looking but corrupt evidence."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_lib import contains_amount, entity_price, _png_ok
from _support import build_run, copy_db, run_verifier
from test_verifiers import honest_traj


def test_swapped_bellevue_prices_fail(tmp_path):
    b = honest_traj(6)
    b.answer(b.traj['final_answer'].replace('$65/mo', '$TEMP/mo').replace('$75/mo', '$65/mo').replace('$TEMP/mo', '$75/mo'))
    run = build_run(tmp_path, 'swapped', b)
    result = run_verifier(6, run)
    assert not result['pass']
    assert 'answer_68_cheapest_5x5' in result['reason']


def test_prices_accept_bullets_and_reject_negated_rate():
    assert entity_price('12465 Northup Way: $65/month; 13640 Bel Red Road: $75/month.', '12465 Northup Way', 65)
    assert not entity_price('12465 Northup Way is not $65/month; it costs $75.', '12465 Northup Way', 65)


def test_money_is_not_a_phone_number_or_reference():
    assert not contains_amount('Rate unavailable. Phone 425-296-6313. Reference 65.', 65)
    assert contains_amount('The online rent is 65 dollars.', 65)


def test_png_signature_without_image_rejected(tmp_path):
    image = tmp_path / 'broken.png'
    image.write_bytes(b'\x89PNG\r\n\x1a\nnot-a-real-image')
    assert not _png_ok(image)
