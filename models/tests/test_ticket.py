import unittest2

from library import testing
from models.ticket import Ticket


class TestTicket(testing.TestCase, unittest2.TestCase):

  def test_defaults(self):
    ticket = Ticket()
    self.assertIsNone(ticket.transaction)

  def test_get_event(self):
    event = self.create_event()
    ticket = self.create_ticket(event=event)
    self.assertIsNotNone(ticket.get_event())
    self.assertEqual(event.key(), ticket.get_event().key())

  def test_put(self):
    event = self.create_event()
    ticket = Ticket(parent=event)
    ticket.put()

    # Ensure ticket member is persisted to the datastore.
    self.assertLength(1, Ticket.all())
    self.assertIsNotNone(ticket.get_event())
    self.assertEqual(event.key(), ticket.get_event().key())

  def test_put_without_parent(self):
    ticket = Ticket()
    self.assertRaises(RuntimeError, ticket.put)
