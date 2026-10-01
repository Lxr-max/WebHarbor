"""Apply reviewed, source-backed article supplements to the asset seed at build time."""
from pathlib import Path
import sqlite3

ARTICLES = {'how-the-standard-deduction-works': ('income-tax', "The standard deduction is a fixed amount eligible taxpayers subtract from adjusted gross income. Itemizing instead deducts eligible individual expenses, such as qualifying mortgage interest and charitable gifts. You generally choose the larger eligible deduction; you do not take both.\n\n## Apply the comparison\n\nCompare your eligible itemized total with the standard deduction for your filing status and tax year. If itemized deductions are lower, the standard deduction generally reduces taxable income more. Keep records supporting any expenses you itemize. Some taxpayers cannot use the standard deduction, and age or blindness can change its amount.\n\n## Sources\n\nThis review supplement summarizes SmartAsset's Standard Deduction guide (https://smartasset.com/taxes/standard-deduction) and IRS Topic 551 (https://www.irs.gov/taxtopics/tc551), accessed September 29, 2026. The linked calculator uses the displayed 2025 baseline and does not model every eligibility exception."), 'roth-ira-vs-traditional-ira-a-side-by-side-comparison': ('ira', 'Traditional IRA contributions may be deductible if you qualify. Deductible contributions and earnings are generally taxed when withdrawn. A Roth IRA uses after-tax contributions with no contribution deduction; qualified Roth distributions are not taxable. Roth eligibility, traditional deduction eligibility, and early withdrawal rules matter.\n\n## Compare equal contributions carefully\n\nThe related calculator projects the same annual dollar contribution to each account and applies the retirement tax rate to the traditional balance. It does not reinvest any current traditional IRA deduction. A larger displayed Roth balance therefore does not by itself prove that Roth is better on an equal take-home-cost basis.\n\n## Sources\n\nThis review supplement summarizes the IRS Traditional and Roth IRAs comparison (https://www.irs.gov/retirement-plans/traditional-and-roth-iras), accessed September 29, 2026. These are educational estimates, not a personal eligibility determination.')}

def migrate(path=None):
    path = Path(path) if path else Path(__file__).resolve().parent / "instance_seed" / "smartasset.db"
    with sqlite3.connect(path) as connection:
        for slug, (calculator, body) in ARTICLES.items():
            row = connection.execute("SELECT body, related_calc FROM articles WHERE slug=?", (slug,)).fetchone()
            if row is None:
                raise RuntimeError(f"Missing source article: {slug}")
            if row != (body, calculator):
                connection.execute("UPDATE articles SET body=?, related_calc=? WHERE slug=?", (body, calculator, slug))

if __name__ == "__main__":
    import sys
    migrate(sys.argv[1] if len(sys.argv) > 1 else None)
