import pytest
from bionumpy.util.testing import assert_bnpdataclass_equal

from climate_health.time_period.period_range import period_range
from climate_health.time_period.dataclasses import Month, Day, Year


def test_period_range():
    start = Month.single_entry(2020, 7)
    end = Month.single_entry(2021, 2)
    true_range = Month(month=[7, 8, 9, 10, 11, 0, 1, 2], year=[2020, 2020, 2020, 2020, 2020, 2021, 2021, 2021])
    assert_bnpdataclass_equal(period_range(start, end), true_range)


def test_period_range_day():
    start = Day.single_entry(2020, 0, 28)
    end = Day.single_entry(2020, 1, 1)
    days = [28, 29, 30, 0, 1]
    true_range = Day([2020]*len(days), [0, 0, 0, 1, 1], days)
    result = period_range(start, end)
    assert_bnpdataclass_equal(result, true_range)