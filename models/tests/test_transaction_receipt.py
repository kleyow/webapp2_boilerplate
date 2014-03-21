import json

import unittest2

import testing
from models.transaction import Transaction
from models.transaction_receipt import TransactionReceipt


class TransactionReceiptTestCase(testing.TestCase, unittest2.TestCase):

  def test_default_values(self):
    transaction_receipt = TransactionReceipt()
    self.assertIsNone(transaction_receipt.owner)
    self.assertIsNone(transaction_receipt.transaction_data)

  def test_load_transaction_data_no_put(self):
    transaction = Transaction()
    transaction.put()
    transaction_receipt = TransactionReceipt(parent=self.create_profile())
    transaction_receipt.load_transaction_data(transaction)

    # Ensure no datastore entry is created.
    self.assertLength(0, TransactionReceipt.all())

  def test_load_transaction_put(self):
    transaction = Transaction()
    transaction.put()
    transaction_receipt = TransactionReceipt(parent=self.create_profile())
    transaction_receipt.load_transaction_data(transaction, put=True)

    # Ensure a transaction receipt is persisted to the datastore.
    self.assertLength(1, TransactionReceipt.all())
    self.assertEqual(transaction_receipt.key(),
                     TransactionReceipt.all().get().key())
    transaction_data = json.loads(transaction_receipt.transaction_data)
    self.assertEqual(transaction.amount, transaction_data['amount'])
    self.assertEqual(transaction.status, transaction_data['status'])
    self.assertEqual(transaction.uuid, transaction_data['uuid'])

  def test_transaction_put_without_parent(self):
    transaction_receipt = TransactionReceipt()
    self.assertRaises(RuntimeError, transaction_receipt.put)
    self.assertLength(0, TransactionReceipt.all())
