from datetime import date, datetime, timedelta

import freezegun
import unittest2

from library import testing
from library.time_helpers import parse_window, WINDOW_DATE_FORMAT


class TestParseWindow(testing.TestCase, unittest2.TestCase):

  def test_parse_window_today(self):
    window, start, end = parse_window('today')
    self.assertEqual('today', window)
    self.assertEqual(datetime.utcnow().date(), start)
    self.assertEqual(datetime.utcnow().date(), end)

  def test_parse_window_yesterday(self):
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    window, start, end = parse_window('yesterday')
    self.assertEqual('yesterday', window)
    self.assertEqual(yesterday, start)
    self.assertEqual(yesterday, end)

  def test_parse_window_this_week(self):
    # Starting wiht Nov 29, here is the day set-up.
    #      29 30 1 2 3 4  5 6  7
    # Day: Sa Su M T W Th F Sa Su
    # parse_window relies on account.get_current_time(), so we can use that
    # to change when "today" is.

    sunday = datetime.now().replace(year=2012, month=9, day=30)
    monday = datetime.now().replace(year=2012, month=10, day=1)
    tuesday = datetime.now().replace(year=2012, month=10, day=2)
    saturday = datetime.now().replace(year=2012, month=10, day=6)
    next_sunday = datetime.now().replace(year=2012, month=10, day=7)

    # First, let's pretend it's Monday (Oct 1).
    with freezegun.freeze_time(monday.strftime('%X %x')):
      # The window 'this-week' should give us Sep 30 (Su) to Oct 1 (today).
      _, start, end = parse_window('this-week')
      self.assertEqual(sunday.date(), start)
      self.assertEqual(monday.date(), end)

    # Next, check what happens when it's Saturday (Oct 6).
    with freezegun.freeze_time(saturday.strftime('%X %x')):
      # The window 'this-week' should give us Sep 30 (Su) to Oct 6 (today).
      _, start, end = parse_window('this-week')
      self.assertEqual(sunday.date(), start)
      self.assertEqual(saturday.date(), end)

    # What happens when it's Sunday (Oct 7).
    with freezegun.freeze_time(next_sunday.strftime('%X %x')):
      _, start, end = parse_window('this-week')
      self.assertEqual(next_sunday.date(), start)
      self.assertEqual(next_sunday.date(), end)

    # Finally, check when the week_start changes from Sunday to Tuesday.
    # If today is Oct 6, then 'this-week' should be
    # Tues (Oct 2) to Sat (Oct 6).
    with freezegun.freeze_time(saturday.strftime('%X %x')):
      _, start, end = parse_window('this-week', week_start=tuesday.weekday())
      self.assertEqual(tuesday.date(), start)
      self.assertEqual(saturday.date(), end)

  def test_parse_window_last_week(self):
    # Starting wiht Nov 29, here is the day set-up.
    #      29 30 1 2 3 4  5 6  7  8 9 10 11 12 13 14
    # Day: Sa Su M T W Th F Sa Su M T W  Th F  S  Su
    # parse_window relies on account.get_current_time(), so we can use that
    # to change when "today" is.

    last_sunday = datetime.now().replace(year=2012, month=9, day=30)
    last_tuesday = datetime.now().replace(year=2012, month=10, day=2)
    last_saturday = datetime.now().replace(year=2012, month=10, day=6)
    sunday = datetime.now().replace(year=2012, month=10, day=7)
    monday = datetime.now().replace(year=2012, month=10, day=8)
    saturday = datetime.now().replace(year=2012, month=10, day=13)

    # First, let's pretend it's Monday (Oct 8).
    with freezegun.freeze_time(monday.strftime('%X %x')):
      # The window 'last-week' should give us Sep 30 (Su) to Oct 6 (Sat).
      _, start, end = parse_window('last-week')
      self.assertEqual(last_sunday.date(), start)
      self.assertEqual(last_saturday.date(), end)

    # Next, check what happens when it's Saturday (Oct 13).
    with freezegun.freeze_time(saturday.strftime('%X %x')):
      # The window 'last-week' should give us Sep 30 (Su) to Oct 6 (Sat).
      _, start, end = parse_window('last-week')
      self.assertEqual(last_sunday.date(), start)
      self.assertEqual(last_saturday.date(), end)

    # What happens when it's Sunday (Oct 7).
    with freezegun.freeze_time(sunday.strftime('%X %x')):
      _, start, end = parse_window('last-week')
      self.assertEqual(last_sunday.date(), start)
      self.assertEqual(last_saturday.date(), end)

    # Finally, check when the week_start changes from Sunday to Tuesday.
    # If today is Oct 13, then 'last-week' should be
    # Tues (Oct 2) to Mon (Oct 8).
    with freezegun.freeze_time(saturday.strftime('%X %x')):
      _, start, end = parse_window('last-week',
                                   week_start=last_tuesday.weekday())
      self.assertEqual(last_tuesday.date(), start)
      self.assertEqual(monday.date(), end)

  def test_parse_window_invalid(self):
    expected = parse_window('today')
    self.assertEqual(expected, parse_window('invalid window'))
    self.assertEqual(expected, parse_window('2011010120120101x'))
    self.assertEqual(expected, parse_window('x2011010120120101'))
    self.assertEqual(expected, parse_window(None))

  def test_parse_window_arbitrary_dates(self):
    start_date, end_date = date(2011, 04, 01), date(2011, 05, 01)
    date_string = '%s-%s' % (start_date.strftime(WINDOW_DATE_FORMAT),
                             end_date.strftime(WINDOW_DATE_FORMAT))
    window, start, end = parse_window(date_string)
    self.assertEqual(date_string, window)
    self.assertEqual(start_date, start)
    self.assertEqual(end_date, end)

  def test_parse_window_arbitrary_dates_known_window(self):
    valid_windows = ['today', 'yesterday', 'this-week', 'last-week']
    # Oct 1, 2012 is a Monday. Since our week_start is on Sunday, this means
    # everything should work.
    monday = datetime.utcnow().replace(year=2012, month=10, day=1)

    with freezegun.freeze_time(monday.strftime('%X %x')):
      for window in valid_windows:
        _, start, end = parse_window(window)
        date_string = '%s-%s' % (start.strftime(WINDOW_DATE_FORMAT),
                                 end.strftime(WINDOW_DATE_FORMAT))

        actual = parse_window(date_string)
        self.assertEqual(window, actual[0])
        self.assertEqual(start, actual[1])
        self.assertEqual(end, actual[2])

  def test_parse_window_arbitrary_dates_known_window_this_week(self):
    # If "today" is the same day as week start, then 'this-week' and 'today'
    # should be the same. We default to choosing 'today'.
    sunday = datetime.utcnow().replace(year=2012, month=9, day=30)

    with freezegun.freeze_time(sunday.strftime('%X %x')):
      _, start, end = parse_window('this-week')
      window, start, end = parse_window('%s-%s' % (
          start.strftime(WINDOW_DATE_FORMAT),
          end.strftime(WINDOW_DATE_FORMAT)))
      self.assertEqual('today', window)
      self.assertEqual(sunday.date(), start)
      self.assertEqual(sunday.date(), end)
