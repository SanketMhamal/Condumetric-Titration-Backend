import json
from django.test import TestCase, Client
from titration.calculation import (
    apply_dilution,
    split_strong,
    split_weak,
    find_equivalence,
)
import numpy as np


class DilutionTest(TestCase):
    def test_no_dilution(self):
        """When v=0, corrected == original."""
        result = apply_dilution([0], [10.0], v0=50.0)
        self.assertAlmostEqual(result[0], 10.0)

    def test_basic_correction(self):
        """Y_corr = Y * (V0 + v) / V0"""
        result = apply_dilution([5.0], [10.0], v0=50.0)
        self.assertAlmostEqual(result[0], 10.0 * 55.0 / 50.0)


class SplitStrongTest(TestCase):
    def test_finds_minimum(self):
        data = [10, 8, 6, 4, 3, 5, 7, 9]
        self.assertEqual(split_strong(data), 4)

    def test_first_element_min(self):
        data = [1, 2, 3, 4]
        self.assertEqual(split_strong(data), 0)


class SplitWeakTest(TestCase):
    def test_finds_sharpest_change(self):
        # Slow rise then sharp rise at index ~5
        data = [1.0, 1.2, 1.4, 1.6, 1.8, 5.0, 9.0, 13.0]
        idx = split_weak(data)
        self.assertGreaterEqual(idx, 3)
        self.assertLessEqual(idx, 6)


class FindEquivalenceStrongTest(TestCase):
    def test_basic_strong(self):
        vols = list(range(0, 10))
        # V-shape: decreasing then increasing
        conds = [20, 18, 16, 14, 12, 10, 12, 14, 16, 18]
        result = find_equivalence(vols, conds, "strong", v0=100.0, apply_dilution_flag=False)
        self.assertIn("equivalence_point", result)
        self.assertIn("angle", result)
        self.assertIn("region_A", result)
        self.assertIn("region_B", result)
        self.assertIn("corrected_data", result)
        # Equivalence volume should be near 5
        self.assertAlmostEqual(result["equivalence_point"]["volume"], 5.0, places=0)


class APIEndpointTest(TestCase):
    def test_calculate_strong(self):
        client = Client()
        payload = {
            "volumes": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "conductivities": [20, 18, 16, 14, 12, 10, 12, 14, 16, 18],
            "acid_type": "strong",
            "v0": 100.0,
            "apply_dilution": False,
        }
        response = client.post(
            "/api/calculate/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("equivalence_point", data)
        self.assertIn("angle", data)

    def test_missing_field(self):
        client = Client()
        payload = {"volumes": [1, 2, 3]}
        response = client.post(
            "/api/calculate/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_mismatched_lengths(self):
        client = Client()
        payload = {
            "volumes": [0, 1, 2],
            "conductivities": [10, 20],
            "acid_type": "strong",
            "v0": 50.0,
            "apply_dilution": True,
        }
        response = client.post(
            "/api/calculate/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
