import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("review_engine", Path(__file__).parents[1] / "verify/contract_engine.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

@pytest.mark.parametrize("answer", ["Home: hot tub not listed", "Home: hot tub never listed", "Home: hot tub incorrect; reference number listed"])
def test_negative_amenity_is_not_positive(answer):
    with pytest.raises(ValueError):
        engine.check_claims(answer, [("amenity", r"home.{0,80}hot tub.{0,30}listed")])

@pytest.mark.parametrize("answer", ["Meal: minimum age not captured; category Dining", "For Meal, minimum age is not listed. For Meal, category is Dining."])
def test_unknown_age_does_not_negate_category(answer):
    engine.check_claims(answer, [("category", r"meal.{0,200}category.{0,18}dining")])


def test_signup_password_accepts_new_salt_and_rejects_wrong_password():
    expected = {"bcrypt_password": "DemoPass123!"}
    for _ in range(2):
        good = engine.bcrypt.hashpw(b"DemoPass123!", engine.bcrypt.gensalt(rounds=4)).decode()
        assert engine.matches(good, expected)
    wrong = engine.bcrypt.hashpw(b"WrongPass123!", engine.bcrypt.gensalt(rounds=4)).decode()
    assert not engine.matches(wrong, expected)
    assert not engine.matches("malformed", expected)


@pytest.mark.parametrize("value, valid", [("2026-10-01", True), ("2027-02-28", True), ("2026-02-30", False), ("20261001", False)])
def test_signup_date_is_valid_but_not_frozen(value, valid):
    assert engine.matches(value, {"iso_date": True}) is valid
