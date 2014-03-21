import datetime

import unittest2

from library import constants, testing
from models.event import Event


class TestEvent(testing.TestCase, unittest2.TestCase):

  def test_defaults(self):
    event = Event()
    self.assertIsNone(event.name)
    self.assertIsNone(event.date)
    self.assertIsNone(event.location)
    self.assertIsNone(event.max_tickets)
    self.assertEqual(0, event.usd_price)
    self.assertEqual(0, event.jmd_price)
    self.assertAlmostEqual(
        datetime.datetime.now(), event.created,
        delta=datetime.timedelta(seconds=5))

  def test_get_organization(self):
    organization = self.create_organization()
    event = Event(parent=organization)
    event.put()
    self.assertEqual(organization.key(), event.get_organization().key())

  def test_put_without_parent(self):
    event = Event()
    self.assertRaises(RuntimeError, event.put)

  def test_put(self):
    organization = self.create_organization()
    event = Event(parent=organization)
    event.put()
    self.assertEqual(organization.key(), event.get_organization().key())

  def test_get_price(self):
    event = self.create_event(usd_price=3000, jmd_price=4000)
    self.assertEqual(3000, event.get_price(constants.USD_CURRENCY))
    self.assertEqual(4000, event.get_price(constants.JMD_CURRENCY))

  def test_get_price_edge_cases(self):
    event = self.create_event()
    self.assertRaises(ValueError, event.get_price, 'jimmy')
