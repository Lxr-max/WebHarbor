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
