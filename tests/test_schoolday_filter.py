import unittest
from datetime import date
from unittest.mock import patch

from main import (
    filterVolunteerItemsForDisplay,
    isSchoolDayOpportunity,
    isWashingtonLegalHoliday,
)


def makeOpportunity(dateText, linkSuffix):
    return {
        "date": dateText,
        "link": f"https://example.com/{linkSuffix}",
        "location": "Seattle",
        "description": "Help the community.",
    }


class SchoolDayFilterTests(unittest.TestCase):
    def test_normal_weekday_is_a_school_day(self):
        self.assertTrue(isSchoolDayOpportunity(makeOpportunity("2030-09-04", "weekday")))

    def test_weekend_is_not_a_school_day(self):
        self.assertFalse(isSchoolDayOpportunity(makeOpportunity("2030-09-07", "weekend")))

    def test_washington_legal_holiday_is_not_a_school_day(self):
        self.assertTrue(isWashingtonLegalHoliday(date(2030, 9, 2)))
        self.assertFalse(isSchoolDayOpportunity(makeOpportunity("2030-09-02", "labor-day")))

    def test_observed_holiday_across_year_boundary_is_included(self):
        self.assertTrue(isWashingtonLegalHoliday(date(2021, 12, 31)))

    def test_all_annual_legal_holidays_are_included(self):
        for dateText in (
            "2030-01-01", "2030-01-21", "2030-02-18", "2030-05-27",
            "2030-06-19", "2030-07-04", "2030-09-02", "2030-11-11",
            "2030-11-28", "2030-11-29", "2030-12-25",
            "2027-06-18", "2027-07-05", "2021-12-31",
        ):
            with self.subTest(date=dateText):
                self.assertTrue(isWashingtonLegalHoliday(date.fromisoformat(dateText)))
                self.assertFalse(isSchoolDayOpportunity(makeOpportunity(dateText, dateText)))

    def test_every_regular_weekday_is_skipped(self):
        for day in range(9, 14):
            with self.subTest(day=day):
                self.assertTrue(isSchoolDayOpportunity(makeOpportunity(f"2030-09-{day:02}", str(day))))

    @patch("main.isFutureOrTodayOpportunity", return_value=True)
    def test_filter_only_removes_school_days_when_enabled(self, _futureCheck):
        opportunities = {
            "Wednesday event": makeOpportunity("2030-09-04", "weekday"),
            "Saturday event": makeOpportunity("2030-09-07", "weekend"),
            "Labor Day event": makeOpportunity("2030-09-02", "labor-day"),
        }

        withoutSchooldays = filterVolunteerItemsForDisplay(
            opportunities,
            10,
            skipSchooldays=True,
        )
        withoutFilter = filterVolunteerItemsForDisplay(
            opportunities,
            10,
            skipSchooldays=False,
        )

        self.assertEqual(
            list(withoutSchooldays),
            ["Saturday event", "Labor Day event"],
        )
        self.assertEqual(list(withoutFilter), list(opportunities))


if __name__ == "__main__":
    unittest.main()
