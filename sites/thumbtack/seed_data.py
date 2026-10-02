#!/usr/bin/env python3
"""Deterministic build-time seeder for the thumbtack mirror.

Reads the tracked source_data_*.json snapshots (captured 2026-09-26) and
materializes them into the SQLite database. Called from app.py at import
time (PYTHONHASHSEED=0 keeps the output byte-reproducible).
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    with open(os.path.join(BASE_DIR, name), encoding='utf-8') as fh:
        return json.load(fh)


def _city_aliases(pros_doc):
    aliases = {}
    for pro in pros_doc['pros']:
        slug = ''.join(c if c.isalnum() else '-' for c in pro['city'].lower()).strip('-')
        aliases[slug] = pro['city']
    return aliases


def build_seed(db):
    """Populate an empty database. Idempotent at the function level."""
    from app import (Category, CostGuide, Pro, Review, CITY_SLUG_ALIASES)

    if Category.query.count() > 0:
        CITY_SLUG_ALIASES.update(_city_aliases(_load('source_data_pros.json')))
        return

    cats_doc = _load('source_data_categories.json')
    pros_doc = _load('source_data_pros.json')
    content = _load('source_data_content.json')

    cat_ids = {}
    for row in cats_doc['categories']:
        cat = Category(slug=row['slug'], name=row['name'], plural=row['plural'],
                       h1=row['h1'], description=row['description'],
                       meta_group=row['meta_group'], icon=row['icon'],
                       image=row['image'], questions=json.dumps(row['questions']),
                       quote_questions=json.dumps(row['quote_questions']),
                       cost_slug=row.get('cost_slug'))
        db.session.add(cat)
        db.session.flush()
        cat_ids[row['slug']] = cat.id

    pro_ids = {}
    for row in pros_doc['pros']:
        pro = Pro(
            service_pk=str(row['service_pk']), slug=row['slug'], name=row['name'],
            category_id=cat_ids[row['category']], city=row['city'],
            state=row['state'], rating=row['rating'],
            review_count=row['review_count'], hires=row['hires'],
            similar_jobs=row['similar_jobs'],
            years_in_business=row['years_in_business'],
            employees=row['employees'],
            background_checked=row['background_checked'],
            top_pro=row['top_pro'],
            top_pro_years=json.dumps(row['top_pro_years']),
            responds_in=row['responds_in'], online_now=row['online_now'],
            great_value=row['great_value'],
            in_high_demand=row['in_high_demand'], bio=row['bio'],
            payment_methods=row['payment_methods'],
            social_media=json.dumps(row['social_media']),
            avatar=row['avatar'], gallery=json.dumps(row['gallery']),
            business_hours=json.dumps(row['business_hours']),
            rating_distribution=json.dumps(row['rating_distribution']),
            review_tags=json.dumps(row['review_tags']),
            services_offered=json.dumps(row['services_offered']),
            card_quote=row['card_quote'], card_quote_author=row['card_quote_author'],
            background_check_name=row.get('background_check_name'),
            credentials_zip=row.get('credentials_zip'))
        db.session.add(pro)
        db.session.flush()
        pro_ids[str(row['service_pk'])] = pro.id
        for rev in row['reviews']:
            db.session.add(Review(pro_id=pro.id, author=rev['author'],
                                  date_str=rev['date_str'], rating=rev['rating'],
                                  body=rev['body'], details=rev.get('details'),
                                  hired=rev.get('hired', False),
                                  source='upstream'))

    for row in content['cost_guides']:
        db.session.add(CostGuide(
            slug=row['slug'], title=row['title'], group_name=row['group_name'],
            avg_price=row.get('avg_price'), range_low=row.get('range_low'),
            range_high=row.get('range_high'), low_end=row.get('low_end'),
            high_end=row.get('high_end'), intro=row['intro'],
            tables=json.dumps(row['tables']), faqs=json.dumps(row['faqs']),
            related_category=row.get('related_category'),
            updated_str=row.get('updated_str', 'Sep 2026')))

    db.session.commit()
    CITY_SLUG_ALIASES.update(_city_aliases(pros_doc))


if __name__ == '__main__':
    # Importing app bootstraps the schema + seed into instance/thumbtack.db.
    from app import app  # noqa: F401
    print('seeded')
