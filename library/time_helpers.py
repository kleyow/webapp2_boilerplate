from datetime import datetime, timedelta
import re

import pytz


WINDOW_DATE_FORMAT = '%Y%m%d'
TIME_FORMAT = '%I:%M %p'


def parse_time(time):
  """Try to parse the input time as HH:MM am/pm.

  Returns:
    datetime.time if successful (None if parsing failed)
  """

  try:
    return datetime.strptime(time, TIME_FORMAT).time()
  except:
    return None


def format_time(time):
  """Format the given time as HH:MM am/pm.

  Returns:
    str representing the time (None if invalid time provided)
  """
  if time:
    return time.strftime(TIME_FORMAT).lstrip('0')


def parse_window(window, timezone=None, week_start=6):
  """Turn a `window` (string) into a start and end date.

  If the window is not valid, defaults to "today".
  week_start is set to Sunday (6) by default.
  timezone is UTC by default.

  Returns:
    (str, datetime, datetime) representing the window, start, and end date
  """
  utc_now = pytz.utc.localize(datetime.utcnow())
  today = utc_now.astimezone(timezone or pytz.utc).date()
  week_start = today - timedelta(days=(today.weekday() -
                                       week_start) % 7)
  valid_windows = {
      'today': (today, today),
      'yesterday': (today - timedelta(days=1),
                    today - timedelta(days=1)),
      'this-week': (week_start, today),
      'last-week': (week_start - timedelta(weeks=1),
                    week_start - timedelta(days=1)),
  }

  # If the window was a valid string, use that.
  if re.match(r'^\d{8}-\d{8}$', window or ''):
    start_string, end_string = window.split('-')
    start = datetime.strptime(start_string, WINDOW_DATE_FORMAT).date()
    end = datetime.strptime(end_string, WINDOW_DATE_FORMAT).date()

    # Do a reverse dictionary search to see if we actually are looking for a
    # common window.
    for key, value in valid_windows.items():
      if value == (start, end):
        window = key

  else:
    if window not in valid_windows:
      window = 'today'

    start, end = valid_windows.get(window)

  return window, start, end
