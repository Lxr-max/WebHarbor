import unittest
from decimal import Decimal, localcontext

import calc


def independent_payoff(balance, annual_rate, payment):
    with localcontext() as ctx:
        ctx.prec = 40
        balance = Decimal(str(balance))
        rate = Decimal(str(annual_rate)) / Decimal("1200")
        payment = Decimal(str(payment))
        months = 0
        interest_total = Decimal("0")
        final_payment = Decimal("0")
        while balance > 0:
            interest = balance * rate
            due = balance + interest
            final_payment = min(payment, due)
            balance = due - final_payment
            interest_total += interest
            months += 1
        return months, interest_total, final_payment


class PayoffTests(unittest.TestCase):
    def test_credit_card_uses_actual_last_payment(self):
        expected_months, expected_interest, expected_final = independent_payoff(
            Decimal("5000"), Decimal("22.5"), Decimal("200")
        )
        result = calc.calc_credit_card({
            "balance": "5000", "apr": "22.5", "monthly_payment": "200"
        })
        self.assertEqual(result["months_to_payoff"], expected_months)
        self.assertAlmostEqual(result["total_interest"], float(expected_interest), 2)
        self.assertAlmostEqual(result["final_payment"], float(expected_final), 2)
        self.assertLess(result["final_payment"], result["monthly"])

    def test_zero_rate_has_no_interest(self):
        result = calc.calc_credit_card({
            "balance": "1000", "apr": "0", "monthly_payment": "120"
        })
        self.assertEqual(result["months_to_payoff"], 9)
        self.assertEqual(result["total_interest"], 0)
        self.assertEqual(result["final_payment"], 40)

    def test_invalid_payoff_boundaries(self):
        invalid = [
            {"balance": "1000", "apr": "-0.1", "monthly_payment": "100"},
            {"balance": "1000", "apr": "12", "monthly_payment": "0"},
            {"balance": "1000", "apr": "12", "monthly_payment": "-1"},
            {"balance": "1000", "apr": "12", "monthly_payment": "10"},
        ]
        for inputs in invalid:
            with self.subTest(inputs=inputs), self.assertRaises(calc.CalcError):
                calc.calc_credit_card(inputs)

    def test_student_loan_finishes_at_contract_term(self):
        result = calc.calc_student_loan({
            "balance": "30000", "rate": "5.5", "term_years": "10", "extra": "0"
        })
        self.assertEqual(result["months_to_payoff"], 120)
        self.assertGreater(result["final_payment"], 0)
        faster = calc.calc_student_loan({
            "balance": "30000", "rate": "5.5", "term_years": "10", "extra": "75"
        })
        self.assertLess(faster["months_to_payoff"], 120)
        self.assertLess(faster["total_interest"], result["total_interest"])


class SavingsAndTaxTests(unittest.TestCase):
    def test_non_finite_numbers_are_rejected(self):
        for value in (
            "nan", "NaN", "inf", "-inf", "Infinity",
            float("nan"), float("inf"), float("-inf"),
        ):
            with self.subTest(value=value), self.assertRaises(calc.CalcError):
                calc.calc_income_tax({"income": value})

    def test_finite_input_overflow_is_a_calculation_error(self):
        with self.assertRaisesRegex(calc.CalcError, "too large"):
            calc.run("retirement", {
                "current_age": "20", "retire_age": "99",
                "life_age": "100", "growth": "1e308",
            })

    def test_apy_is_effective_annual_yield(self):
        initial = Decimal("5000")
        monthly = Decimal("200")
        annual_yield = Decimal("0.04")
        months = 120
        monthly_yield = (Decimal("1") + annual_yield) ** (
            Decimal("1") / Decimal("12")
        ) - Decimal("1")
        expected = (
            initial * (Decimal("1") + annual_yield) ** Decimal("10")
            + monthly
            * (((Decimal("1") + monthly_yield) ** months - Decimal("1"))
               / monthly_yield)
        )
        result = calc.calc_savings({
            "initial": "5000", "monthly_deposit": "200",
            "years": "10", "apy": "4"
        })
        self.assertAlmostEqual(result["final_balance"], float(expected), 2)

    def test_savings_boundaries(self):
        zero = calc.calc_savings({
            "initial": "1000", "monthly_deposit": "100",
            "years": "1", "apy": "0"
        })
        self.assertEqual(zero["final_balance"], 2200)
        for field, value in (("initial", "-1"), ("monthly_deposit", "-1")):
            inputs = {
                "initial": "1000", "monthly_deposit": "100",
                "years": "1", "apy": "4", field: value
            }
            with self.subTest(field=field), self.assertRaises(calc.CalcError):
                calc.calc_savings(inputs)
        with self.assertRaises(calc.CalcError):
            calc.calc_savings({
                "initial": "1000", "monthly_deposit": "100",
                "years": "1", "apy": "-100"
            })
        with self.assertRaises(calc.CalcError):
            calc.calc_savings({
                "initial": "1000", "monthly_deposit": "100",
                "years": "0", "apy": "4"
            })

    def test_task_calculator_amount_and_age_boundaries(self):
        invalid_calls = [
            (calc.calc_mortgage, {
                "price": "350000", "down": "-1", "rate": "7",
            }),
            (calc.calc_cd, {
                "principal": "-100", "apy": "4", "term_months": "12",
            }),
            (calc.calc_cost_of_living, {
                "city_a": "austin-tx", "city_b": "new-york-ny",
                "salary": "-1",
            }),
            (calc.calc_retirement, {
                "current_age": "40", "retire_age": "67", "life_age": "60",
            }),
            (calc.calc_net_worth, {"cash": "-1"}),
        ]
        for calculator, inputs in invalid_calls:
            with self.subTest(calculator=calculator.__name__):
                with self.assertRaises(calc.CalcError):
                    calculator(inputs)

    def test_2025_deduction_and_bracket_boundary(self):
        below = calc.calc_income_tax({
            "income": "15750", "filing": "single",
            "pretax_401k": "0", "itemized": "0"
        })
        self.assertEqual(below["tax_year"], 2025)
        self.assertEqual(below["taxable_income"], 0)
        self.assertEqual(below["federal_tax"], 0)
        boundary = calc.calc_income_tax({
            "income": str(15750 + 11925), "filing": "single",
            "pretax_401k": "0", "itemized": "0"
        })
        self.assertEqual(boundary["federal_tax"], 1192.5)
        self.assertEqual(boundary["marginal_rate"], 10)

    def test_state_workflows_are_deterministic_and_labeled(self):
        none = calc.calc_state_tax(
            {"income": "90000", "state": "TX", "filing": "single"}
        )
        flat = calc.calc_state_tax(
            {"income": "90000", "state": "PA", "filing": "single"}
        )
        bracket = calc.calc_state_tax(
            {"income": "90000", "state": "CA", "filing": "single"}
        )
        self.assertEqual(none["state_tax"], 0)
        self.assertAlmostEqual(
            flat["state_tax"],
            float(Decimal(str(flat["taxable_income"])) * Decimal("0.0307")),
            2,
        )
        self.assertGreater(bracket["state_tax"], 0)
        self.assertIn("Simplified 2025 planning estimate", bracket["method_note"])

    def test_negative_tax_inputs_rejected(self):
        with self.assertRaises(calc.CalcError):
            calc.calc_income_tax({"income": "-1"})
        with self.assertRaises(calc.CalcError):
            calc.calc_state_tax({"income": "-1", "state": "CA"})


if __name__ == "__main__":
    unittest.main()
