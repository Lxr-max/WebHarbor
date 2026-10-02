"""Regression tests for the offline grading boundary; no live database required."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contract_engine import check_state, check_claims, digest

class GradingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.initial={'orders':{'[1]':{'id':1,'user':7,'total':35,'status':'pending'}}}
        self.spec={'initial_digest':digest(self.initial),'state':{'orders':{'updated':{'[1]':{'status':'paid'}}}}}
        self.after=copy.deepcopy(self.initial);self.after['orders']['[1]']['status']='paid'

    def test_intended_update(self):
        check_state(self.initial,self.after,self.spec)

    def test_unrelated_owner_change_rejected(self):
        self.after['orders']['[1]']['user']=9
        with self.assertRaises(ValueError):check_state(self.initial,self.after,self.spec)

    def test_noop_rejected(self):
        with self.assertRaises(ValueError):check_state(self.initial,self.initial,self.spec)

    def test_existing_deletion_rejected(self):
        self.after['orders'].clear()
        with self.assertRaises(ValueError):check_state(self.initial,self.after,self.spec)

    def test_extra_row_rejected(self):
        self.after['orders']['[2]']={'id':2,'user':7,'total':35,'status':'paid'}
        with self.assertRaises(ValueError):check_state(self.initial,self.after,self.spec)

    def test_seed_mismatch_rejected(self):
        self.initial['orders']['[1]']['total']=45
        with self.assertRaises(ValueError):check_state(self.initial,self.after,self.spec)

    def test_equivalent_currency_and_words(self):
        claims=[('cost',r'total charged.{0,12}1234\.50'),('bags',r'2 free bags')]
        for text in ['Total charged: $1,234.50. Two free bags.', '- Total charged: $1234.50\n- 2 complimentary bags.']:
            check_claims(text,claims)

    def test_wrong_price_rejected(self):
        with self.assertRaises(ValueError):check_claims('Total charged: $35; reference 45',[('cost',r'total charged.{0,10}\$45\b')])

    def test_negated_number_rejected(self):
        with self.assertRaises(ValueError):check_claims('Total charged: not $45',[('cost',r'total charged.{0,15}\$45\b')])

    def test_entity_swapped_values_rejected(self):
        with self.assertRaises(ValueError):check_claims('Flight 2790: $210.95. Flight 2803: $202.95.', [('2790 cost',r'2790.{0,15}202\.95'),('2803 cost',r'2803.{0,15}210\.95')])

if __name__=='__main__':unittest.main()
