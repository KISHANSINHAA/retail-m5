"""
Unit tests for ETL pipeline and data preprocessing.
"""
from __future__ import annotations

import os
import shutil
import unittest
import pandas as pd
from pathlib import Path

from src.config import settings
from src.generate_mock_data import generate_mock_m5_data


class TestRetailSenseETL(unittest.TestCase):
    """Test suite for ingestion and preprocessing verification."""

    @classmethod
    def setUpClass(cls):
        # Override paths to test workspace
        cls.test_dir = Path(__file__).resolve().parent / "test_data"
        cls.test_dir.mkdir(parents=True, exist_ok=True)

        settings.raw_dir = cls.test_dir / "raw"
        settings.bronze_dir = cls.test_dir / "bronze"
        settings.silver_dir = cls.test_dir / "silver"
        settings.gold_dir = cls.test_dir / "gold"
        settings.models_dir = cls.test_dir / "models"
        settings.log_file = cls.test_dir / "logs/app.log"
        settings.sample_limit = 5

        settings.ensure_dirs()

    @classmethod
    def tearDownClass(cls):
        # Clean up test directories
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)

    def test_01_mock_data_generation(self):
        """Verify that synthetic CSV generation works and conforms to M5 schemas."""
        generate_mock_m5_data()

        calendar_path = settings.raw_dir / "calendar.csv"
        prices_path = settings.raw_dir / "sell_prices.csv"
        sales_path = settings.raw_dir / "sales_train_validation.csv"

        self.assertTrue(calendar_path.exists(), "calendar.csv should exist")
        self.assertTrue(prices_path.exists(), "sell_prices.csv should exist")
        self.assertTrue(sales_path.exists(), "sales_train_validation.csv should exist")

        # Load and verify shapes and columns
        df_cal = pd.read_csv(calendar_path)
        df_pr = pd.read_csv(prices_path)
        df_sal = pd.read_csv(sales_path)

        self.assertIn("date", df_cal.columns)
        self.assertIn("d", df_cal.columns)
        self.assertIn("sell_price", df_pr.columns)
        self.assertIn("id", df_sal.columns)

        # Sales horizontal format: d_1 to d_365 should be columns
        self.assertIn("d_1", df_sal.columns)
        self.assertIn("d_365", df_sal.columns)


if __name__ == "__main__":
    unittest.main()
