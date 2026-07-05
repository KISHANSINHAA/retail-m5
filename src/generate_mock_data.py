"""
Generate mock M5 Forecasting dataset (calendar.csv, sell_prices.csv, sales_train_validation.csv)
for local testing, development, and validation.
"""
from __future__ import annotations

import csv
import datetime
import random
from pathlib import Path
from src.config import settings
from src.logger import logger


def generate_mock_m5_data():
    """Generates synthetic CSV files matching the M5 schema."""
    settings.ensure_dirs()
    raw_dir = settings.raw_dir

    num_days = 365
    forecast_days = 30
    total_days = num_days + forecast_days

    # Define products, departments, categories, stores, states
    states = ["CA", "TX", "WI"]
    stores_by_state = {
        "CA": ["CA_1", "CA_2"],
        "TX": ["TX_1", "TX_2"],
        "WI": ["WI_1", "WI_2"],
    }
    all_stores = []
    for s_list in stores_by_state.values():
        all_stores.extend(s_list)

    categories = ["HOBBIES", "HOUSEHOLD", "FOODS"]
    departments_by_cat = {
        "HOBBIES": ["HOBBIES_1", "HOBBIES_2"],
        "HOUSEHOLD": ["HOUSEHOLD_1", "HOUSEHOLD_2"],
        "FOODS": ["FOODS_1", "FOODS_2"],
    }

    # Generate small set of items (e.g. 5 items per category-dept combination)
    items = []
    item_details = {}  # item_id -> (cat_id, dept_id)
    for cat in categories:
        for dept in departments_by_cat[cat]:
            for i in range(1, 4):  # 3 items per department
                item_id = f"{dept}_{i:03d}"
                items.append(item_id)
                item_details[item_id] = (cat, dept)

    logger.info(f"Generating mock data schema: {len(all_stores)} stores, {len(items)} items.")

    # 1. Generate calendar.csv
    calendar_path = raw_dir / "calendar.csv"
    logger.info(f"Writing mock calendar to {calendar_path}")

    start_date = datetime.date(2011, 1, 29)
    calendar_rows = []

    # Holiday lists
    holidays = {
        "SuperBowl": ["2011-02-06", "2012-02-05"],
        "Thanksgiving": ["2011-11-24", "2012-11-22"],
        "Christmas": ["2011-12-25", "2012-12-25"],
        "LaborDay": ["2011-09-05", "2012-09-03"],
        "MemorialDay": ["2011-05-30", "2012-05-28"],
    }
    holiday_types = {
        "SuperBowl": "Sporting",
        "Thanksgiving": "National",
        "Christmas": "National",
        "LaborDay": "National",
        "MemorialDay": "National",
    }

    for day_idx in range(1, total_days + 1):
        curr_date = start_date + datetime.timedelta(days=day_idx - 1)
        date_str = curr_date.strftime("%Y-%m-%d")

        # wm_yr_wk formula: starts at 11101 (2011, year week 1)
        # Simple weekly calculation for mock data:
        weeks_since_start = (curr_date - datetime.date(2011, 1, 29)).days // 7
        year_offset = curr_date.year - 2000
        # simple calculation of week of year
        week_num = curr_date.isocalendar()[1]
        wm_yr_wk = int(f"{year_offset:02d}{week_num:02d}")

        weekday = curr_date.strftime("%A")
        # 1 for Saturday, 2 for Sunday, ..., 7 for Friday
        # isocalendar weekday: 1 (Mon) - 7 (Sun)
        iso_wd = curr_date.isocalendar()[2]
        wday = 3 if iso_wd == 1 else (4 if iso_wd == 2 else (5 if iso_wd == 3 else (6 if iso_wd == 4 else (7 if iso_wd == 5 else (1 if iso_wd == 6 else 2)))))

        month = curr_date.month
        year = curr_date.year
        d = f"d_{day_idx}"

        # Events
        event_name_1 = ""
        event_type_1 = ""
        for hname, hdates in holidays.items():
            if date_str in hdates:
                event_name_1 = hname
                event_type_1 = holiday_types[hname]
                break

        # SNAP flags (simulate SNAP schedules)
        # CA SNAP: first 10 days of month
        # TX SNAP: 1st to 15th
        # WI SNAP: 1st to 14th
        snap_CA = 1 if curr_date.day <= 10 else 0
        snap_TX = 1 if curr_date.day <= 15 else 0
        snap_WI = 1 if curr_date.day <= 14 else 0

        calendar_rows.append({
            "date": date_str,
            "wm_yr_wk": wm_yr_wk,
            "weekday": weekday,
            "wday": wday,
            "month": month,
            "year": year,
            "d": d,
            "event_name_1": event_name_1,
            "event_type_1": event_type_1,
            "event_name_2": "",
            "event_type_2": "",
            "snap_CA": snap_CA,
            "snap_TX": snap_TX,
            "snap_WI": snap_WI,
        })

    with open(calendar_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=calendar_rows[0].keys())
        writer.writeheader()
        writer.writerows(calendar_rows)

    # 2. Generate sell_prices.csv
    sell_prices_path = raw_dir / "sell_prices.csv"
    logger.info(f"Writing mock sell prices to {sell_prices_path}")

    # Extract unique wm_yr_wk values
    unique_weeks = sorted(list(set(row["wm_yr_wk"] for row in calendar_rows)))

    price_rows = []
    # Store-item price variations
    base_prices = {item_id: round(random.uniform(1.5, 12.0), 2) for item_id in items}

    for store_id in all_stores:
        for item_id in items:
            base_p = base_prices[item_id]
            # Add store-specific offset
            store_price = max(0.5, round(base_p + random.uniform(-0.5, 0.5), 2))
            for wk in unique_weeks:
                # Add tiny random week variation
                p = max(0.49, round(store_price + random.choice([-0.05, 0.0, 0.05]), 2))
                price_rows.append({
                    "store_id": store_id,
                    "item_id": item_id,
                    "wm_yr_wk": wk,
                    "sell_price": p,
                })

    with open(sell_prices_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["store_id", "item_id", "wm_yr_wk", "sell_price"])
        writer.writeheader()
        writer.writerows(price_rows)

    # 3. Generate sales_train_validation.csv
    sales_path = raw_dir / "sales_train_validation.csv"
    logger.info(f"Writing mock sales_train_validation to {sales_path}")

    sales_rows = []
    d_cols = [f"d_{i}" for i in range(1, num_days + 1)]

    # Generate daily sales
    for store_id in all_stores:
        state_id = store_id.split("_")[0]
        for item_id in items:
            cat_id, dept_id = item_details[item_id]
            row_id = f"{item_id}_{store_id}_validation"

            row = {
                "id": row_id,
                "item_id": item_id,
                "dept_id": dept_id,
                "cat_id": cat_id,
                "store_id": store_id,
                "state_id": state_id,
            }

            # Generate sales with seasonality
            # HOBBIES: low sales, FOODS: high sales, HOUSEHOLD: medium sales
            base_rate = 0.5 if cat_id == "HOBBIES" else (1.5 if cat_id == "HOUSEHOLD" else 4.0)

            # Weekly pattern (higher sales on weekends: wday 1 & 2)
            for day_idx in range(1, num_days + 1):
                cal_info = calendar_rows[day_idx - 1]
                wday = cal_info["wday"]
                is_weekend = 1 if wday in [1, 2] else 0

                # Rate modulation
                rate = base_rate
                if is_weekend:
                    rate *= 1.4
                if cal_info["event_name_1"]:
                    rate *= 1.25  # sales bump on holiday

                # Add state SNAP program boost
                snap_active = cal_info[f"snap_{state_id}"]
                if snap_active and cat_id == "FOODS":
                    rate *= 1.2

                # Add some trend/random walk
                rate += (day_idx / num_days) * 0.2

                # Generate integer sales using Poisson-like logic
                sales = max(0, int(random.expovariate(1.0 / rate))) if rate > 0 else 0
                row[f"d_{day_idx}"] = sales

            sales_rows.append(row)

    with open(sales_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"] + d_cols
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sales_rows)

    logger.info("Mock M5 dataset successfully created.")


if __name__ == "__main__":
    generate_mock_m5_data()
