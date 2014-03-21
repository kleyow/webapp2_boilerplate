from datetime import datetime

import pytz


def get_common_timezones():
  now = datetime.now()
  timezones = []

  for name in pytz.common_timezones:
    timezone = pytz.timezone(name)
    utc_offset = timezone.utcoffset(now)
    offset = utc_offset.seconds / 3600 + utc_offset.days * 24

    offset_display = '%02d:00' % abs(offset)
    if offset < 0:
      offset_display = '-%s' % offset_display

    timezones.append({'name': name, 'offset': offset,
                      'offset_display': offset_display})

  timezones.sort(key=lambda tz: tz['offset'])

  return timezones
