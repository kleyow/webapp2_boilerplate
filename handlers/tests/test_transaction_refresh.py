import unittest2

from library import testing
from models.transaction import Transaction


class TestTransactionRefresh(testing.TestCase, unittest2.TestCase):

  def test_transaction_refresh_returns_correct_json(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer)
    response = self.app.get(
        self.uri_for('transaction.refresh', uuid=transaction.uuid))
    self.assertOk(response)
    expected_response = {'transaction_status': transaction.status}
    self.assertEqual(expected_response, response.json)

  def test_transaction_refresh_empty_transaction(self):
    response = self.app.get(self.uri_for('transaction.refresh'), status=404)
    self.assertNotFound(response)

  def test_transaction_refresh_nonexistent_transaction(self):
    response = self.app.get(
        self.uri_for('transaction.refresh', uuid='INVALID'), status=404)
    self.assertNotFound(response)
