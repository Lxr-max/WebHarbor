"""Bring the packaged Mayo Clinic seed to the schema expected by app.py."""

import argparse
import sqlite3
from pathlib import Path


REQUIRED_COLUMNS = {
    "referral_request": {"preferred_date": "VARCHAR(40)"},
    "second_opinion": {
        "diagnosis_year": "INTEGER",
        "records_count": "INTEGER",
    },
    "international_inquiry": {"visa_support": "BOOLEAN DEFAULT 0"},
    "donation": {
        "tribute_type": "VARCHAR(20)",
        "card_last4": "VARCHAR(4)",
        "donor_phone": "VARCHAR(40)",
        "billing_zip": "VARCHAR(20)",
    },
    "newsletter_signup": {
        "name": "VARCHAR(200)",
        "frequency": "VARCHAR(20) DEFAULT 'weekly'",
        "confirmation_code": "VARCHAR(40)",
    },
}


def missing_columns(connection):
    missing = []
    for table, columns in REQUIRED_COLUMNS.items():
        present = {
            row[1]
            for row in connection.execute(f'PRAGMA table_info("{table}")')
        }
        missing.extend(
            (table, column, declaration)
            for column, declaration in columns.items()
            if column not in present
        )
    return missing


def migrate(path):
    with sqlite3.connect(path) as connection:
        for table, column, declaration in missing_columns(connection):
            connection.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{column}" {declaration}'
            )
        trial_count = connection.execute(
            "SELECT COUNT(*) FROM clinical_trial"
        ).fetchone()[0]
        if trial_count == 40:
            rows = connection.execute(
                "SELECT id FROM clinical_trial ORDER BY id"
            ).fetchall()
            for index, (row_id,) in enumerate(rows, start=1):
                connection.execute(
                    "UPDATE clinical_trial SET nct_id = ? WHERE id = ?",
                    (f"SIM-MAYO-{index:03d}", row_id),
                )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "database",
        nargs="?",
        type=Path,
        default=Path(__file__).parent / "instance_seed" / "mayo_clinic.db",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with sqlite3.connect(args.database) as connection:
        missing = missing_columns(connection)
        invalid_ids = connection.execute(
            "SELECT nct_id FROM clinical_trial WHERE nct_id NOT LIKE 'SIM-MAYO-%'"
        ).fetchall()
    if args.check:
        if missing or invalid_ids:
            raise SystemExit(
                f"seed migration required: columns={missing}, trial_ids={invalid_ids[:3]}"
            )
        return
    migrate(args.database)


if __name__ == "__main__":
    main()
