import mock
import unittest2

from library.analytics import Analytics
from library import testing


class TestAnalytics(testing.TestCase, unittest2.TestCase):

  def test_analytics_track_event_adds_flash(self):
    session = mock.Mock()
    analytics = Analytics(mock.Mock(session=session))

    # Check that calling track_event executes the add_flash method.
    analytics.track_event('category', 'event')
    self.assertEqual(1, session.add_flash.call_count)

    expected_args = {'key': Analytics.FLASH_KEY,
                     'value': ('category', 'event')}
    self.assertEqual((expected_args, ), session.add_flash.call_args)

  def test_analytics_get_events(self):
    # The format for flashes is [(value, level), ...].
    flashes = [(('category', 'action'), None)]
    session = mock.Mock()
    session.get_flashes = mock.Mock(return_value=flashes)
    analytics = Analytics(mock.Mock(session=session))

    # Check that we get just the category and action back.
    # get_events returns a generator, but that's irrelevant.
    events = analytics.get_events()
    self.assertEqual([('category', 'action')], list(events))

    # Check that we are retrieving flashes from the correct key.
    expected_args = {'key': Analytics.FLASH_KEY}
    self.assertEqual((expected_args, ), session.get_flashes.call_args)
