from google.appengine.ext import deferred
import mock
import unittest2
import stripe

from library import constants, locking, testing
from models.funding_source import FundingSource
from models.organization import Organization
from models.profile import Profile
from models.transaction import Transaction
from models.transaction_receipt import TransactionReceipt


class TestTransactionProcess(testing.TestCase, unittest2.TestCase):

  def test_transaction_process_fails_outside_task_queue(self):
    sender = self.create_profile('sender@example.com')
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_organization()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        transaction_type=Transaction.Type.Purchase)

    # Ensure transactions cannot be processed outside of the app engine task
    # queue, and ensure the error is logged.
    with mock.patch('logging.error') as error_logger:
      params = {'transaction_key': str(transaction.key())}
      response = self.app.post(self.uri_for('transaction.process'), params)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)
      error_logger.assert_called_with(Transaction.Errors.UnauthorizedRequest)

    # Reload balances and ensure they haven't changed.
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  def test_transaction_process_fails_without_a_transaction_key(self):
    with mock.patch('logging.error') as error_logger:
      params = {'transaction_key': ''}
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)
      error_logger.assert_called_with(Transaction.Errors.EmptyTransactionKey)

  def test_completed_transactions_cannot_be_processed(self):
    sender = self.create_profile('sender@example.com')
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_organization()
    transaction = self.create_transaction(
        status=Transaction.Status.Completed, sender=sender,
        recipient=recipient, amount=2000,
        transaction_type=Transaction.Type.Purchase)

    # Ensure that to process a completed transactions cannot be processed.
    with mock.patch('logging.error') as error_logger:
      params = {'transaction_key': str(transaction.key())}
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Reload accounts and ensure balances haven't changed.
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  def test_cancelled_transactions_cannot_be_processed(self):
    sender = self.create_profile('sender@example.com')
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_organization()
    transaction = self.create_transaction(
        status=Transaction.Status.Cancelled, sender=sender,
        recipient=recipient, amount=2000,
        transaction_type=Transaction.Type.Purchase)

    # Ensure that cancelled transactions cannot be processed.
    with mock.patch('logging.error') as error_logger:
      params = {'transaction_key': str(transaction.key())}
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Reload sender and recipient and ensure their balances have not changed.
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  def test_invalid_transaction_keys_cannot_be_processed(self):
    # Ensure that the transaction is not processed and the error is logged.
    with mock.patch('logging.error') as error_logger:
      params = {'transaction_key': 'INVALID'}
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

  def test_sender_cannot_send_funds_to_themselves(self):
    sender = self.create_profile()
    sender.usd_balance = 5000
    sender.put()
    transaction = self.create_transaction(
        sender=sender, recipient=sender, amount=2000,
        transaction_type=Transaction.Type.Transfer)

    # Ensure that the transaction is not processed, and the error is logged.
    with mock.patch('logging.error') as error_logger:
      params = {'transaction_key': str(transaction.key())}
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Reload transaction and ensure it has been cancelled.
    transaction = Transaction.get(transaction.key())
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Reload accounts and ensure the balances are unchanged.
    sender = Profile.get(sender.key())
    self.assertEqual(5000, sender.usd_balance)

  @testing.logged_in
  def test_transfer_purchase_exception_on_transfer(self):
    recipient = self.create_organization()
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 5000
    current_profile.put()

    self.assertLength(0, Transaction.all())

    # Ensure a pending transaction is created.
    params = {'amount': '20.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(response, self.uri_for('transaction.view',
                                                id=transaction.key().id()))

    transaction = Transaction.get(transaction.key())
    self.assertEqual(Transaction.Status.Pending, transaction.status)

    # Ensure that a task is placed in the queue to process the task, and that
    # the parameters are correct.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(transaction.key()), params['transaction_key'])

    with self.datastore_consistency_policy(testing.HR_HIGH_CONSISTENCY_POLICY):
      # Make the transfer_funds function raise an exception to ensure
      # transactions are completely atomic.
      with mock.patch.object(Transaction, 'transfer_funds') as transfer:
        transfer.side_effect = Exception

        # Ensure the exception is properly logged.
        with mock.patch('logging.exception') as exception_logger:
          try:
            response = self.app.post(task.url, params,
                                     headers=self.TASKQUEUE_HEADERS)
          finally:
            self.assertTrue(exception_logger.called)
            self.assertEqual(1, exception_logger.call_count)

    # Get current versions of the sender, recipient and transaction, and
    # ensure the balances are unchanged, and that the transaction is
    # cancelled.
    current_profile = Profile.get(current_profile.key())
    recipient = Organization.get(recipient.key())
    transaction = Transaction.get(transaction.key())
    self.assertEqual(5000, current_profile.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

  @testing.logged_in
  def test_transaction_cannot_occur_when_any_party_is_locked(self):
    recipient = self.create_organization()
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 5000
    current_profile.put()

    self.assertLength(0, Transaction.all())
    params = {'amount': '20.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(response, self.uri_for('transaction.view',
                                                id=transaction.key().id()))
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)
    task, = tasks

    # Ensure that a locked sender causes an exception to be raised.
    with locking.lock(str(current_profile.key())):
      with testing.silence_logging():
        response = self.app.post(task.url, task.extract_params(),
                                 headers=self.TASKQUEUE_HEADERS, status=500)
        self.assertEqual(500, response.status_int)

    # Ensure that the transaction has not been cancelled.
    transaction = Transaction.get(transaction.key())
    self.assertEqual(Transaction.Status.Processing, transaction.status)

  def test_declined_credit_card_cancels_transaction(self):
    customer = self.create_profile()
    customer.put()
    funding_source = self.create_funding_source(
        parent=customer, status=FundingSource.Status.Accepted)
    transaction = self.create_transaction(
        funding_source=funding_source,
        transaction_type=Transaction.Type.Deposit, amount=2000)

    # Simulate a declined credit card.
    with mock.patch('stripe.Charge.create') as stripe_charge:
      # stripe.CardError takes 3 args: message, param and code. Since we
      # don't have any use for them in this test, just use dummy strings.
      stripe_charge.side_effect = stripe.CardError('message', 'params',
                                                   'code')
      params = {'transaction_key': str(transaction.key())}

      # Ensure error is logged.
      with mock.patch('logging.exception') as exception_logger:
        response = self.app.post(self.uri_for('transaction.process'), params,
                                 headers=self.TASKQUEUE_HEADERS)
        self.assertOk(response)
        self.assertTrue(exception_logger.called)
        self.assertEqual(1, exception_logger.call_count)

    # Reload transaction and ensure it has been cancelled.
    transaction = Transaction.get(transaction.key())
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure customer's balance has not been incremented.
    customer = Profile.get(customer.key())
    self.assertEqual(0, customer.usd_balance)

  def test_rejected_funding_source_logs_error(self):
    profile = self.create_profile()
    funding_source = self.create_funding_source(
        parent=profile,
        status=FundingSource.Status.Rejected)
    transaction = self.create_transaction(
        funding_source=funding_source,
        transaction_type=Transaction.Type.Deposit, amount=2000)

    with mock.patch('logging.error') as error_logger:
      params = {'transaction_key': str(transaction.key())}
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Ensure profile balance has not been updated.
    profile = Profile.get(profile.key())
    self.assertEqual(0, profile.usd_balance)

  def test_pending_funding_source_logs_error(self):
    profile = self.create_profile()
    funding_source = self.create_funding_source(parent=profile)
    transaction = self.create_transaction(
        funding_source=funding_source,
        transaction_type=Transaction.Type.Deposit, amount=2000)

    with mock.patch('logging.error') as error_logger:
      params = {'transaction_key': str(transaction.key())}
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Ensure profile balance has not been updated.
    profile = Profile.get(profile.key())
    self.assertEqual(0, profile.usd_balance)

  def test_debug_logger_called_correct_amount_of_times(self):
    sender = self.create_profile(usd_balance=5000)
    recipient = self.create_profile()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient,
        transaction_type=Transaction.Type.Transfer, amount=2000)

    # Ensure the debug logger is called 5 times while processing a successful
    # transaction.
    with mock.patch('logging.debug') as debug_logger:
      params = {'transaction_key': str(transaction.key())}
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(debug_logger.called)
      self.assertEqual(5, debug_logger.call_count)

    # Ensure transaction completed successfully.
    transaction = Transaction.get(transaction.key())
    self.assertEqual(Transaction.Status.Completed, transaction.status)

  def test_successful_topup_creates_receipt(self):
    profile = self.create_profile()
    funding_source = self.create_funding_source(
        parent=profile, status=FundingSource.Status.Accepted)
    transaction = self.create_transaction(
        recipient=profile, amount=2000, funding_source=funding_source,
        transaction_type=Transaction.Type.Deposit)

    params = {'transaction_key': str(transaction.key())}

    with mock.patch('stripe.Charge.create') as stripe_charge:
      stripe_charge.return_value = mock.Mock(id='ch_1stsWjqBqYSOtr')
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Ensure a receipt was created.
    self.assertLength(1, TransactionReceipt.all())
    transaction_receipt = TransactionReceipt.all().get()
    self.assertEqual(profile.key(), transaction_receipt.get_owner().key())

  def test_successful_transfer_creates_receipt(self):
    sender = self.create_profile(usd_balance=5000)
    recipient = self.create_profile()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        transaction_type=Transaction.Type.Transfer)

    params = {'transaction_key': str(transaction.key())}

    with self.datastore_consistency_policy(testing.HR_LOW_CONSISTENCY_POLICY):
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Ensure receipts were created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    sender_receipt, recipient_receipt = TransactionReceipt.all()
    self.assertEqual(recipient.key(), recipient_receipt.get_owner().key())
    self.assertEqual(sender.key(), sender_receipt.get_owner().key())

  def test_successful_purchase_creates_receipt(self):
    sender = self.create_profile(usd_balance=5000)
    recipient = self.create_organization()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        transaction_type=Transaction.Type.Purchase)

    params = {'transaction_key': str(transaction.key())}

    with self.datastore_consistency_policy(testing.HR_LOW_CONSISTENCY_POLICY):
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Ensure receipts were created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    recipient_receipt, sender_receipt = TransactionReceipt.all()
    self.assertEqual(recipient.key(), recipient_receipt.get_owner().key())
    self.assertEqual(sender.key(), sender_receipt.get_owner().key())

  def test_cancelled_transfer_creates_receipt(self):
    sender = self.create_profile(usd_balance=5000)
    recipient = self.create_organization()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        transaction_type=Transaction.Type.Purchase)

    params = {'transaction_key': str(transaction.key())}

    with self.datastore_consistency_policy(testing.HR_LOW_CONSISTENCY_POLICY):
      # Simulate a cancelled transaction and ensure receipts are created.
      with mock.patch.object(Transaction, 'transfer_funds') as transfer:
        transfer.side_effect = Exception

        # Mock out exception logger to prevent log spam.
        with mock.patch('logging.exception') as exception_logger:
          response = self.app.post(self.uri_for('transaction.process'), params,
                                   headers=self.TASKQUEUE_HEADERS)
          self.assertOk(response)
          self.assertTrue(exception_logger.called)
          self.assertEqual(1, exception_logger.call_count)

    # Ensure receipts were created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    recipient_receipt, sender_receipt = TransactionReceipt.all()
    self.assertEqual(recipient.key(), recipient_receipt.get_owner().key())
    self.assertEqual(sender.key(), sender_receipt.get_owner().key())

  def test_process_jmd_transfer(self):
    sender = self.create_profile(jmd_balance=5000)
    recipient = self.create_profile()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Transfer)

    params = {'transaction_key': str(transaction.key())}
    response = self.app.post(self.uri_for('transaction.process'), params,
                             headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Ensure balances update correctly, and transaction is marked as
    # completed.
    transaction = Transaction.get(transaction.key())
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(3000, sender.jmd_balance)
    self.assertEqual(2000, recipient.jmd_balance)

    # Ensure the USD balances were not modified.
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  def test_process_jmd_purchase(self):
    sender = self.create_profile(jmd_balance=5000)
    recipient = self.create_organization()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    params = {'transaction_key': str(transaction.key())}
    response = self.app.post(self.uri_for('transaction.process'), params,
                             headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Ensure balances update correctly, and transaction is marked as
    # completed.
    transaction = Transaction.get(transaction.key())
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(3000, sender.jmd_balance)
    self.assertEqual(2000, recipient.jmd_balance)

    # Ensure the USD balances were not modified.
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  @testing.logged_in
  def test_process_deleted_transaction(self):
    # Create a transaction and add it to the queue.
    recipient = self.create_organization()
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 5000
    current_profile.put()

    self.assertLength(0, Transaction.all())

    # Ensure a pending transaction is created.
    params = {'amount': '30.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(response, self.uri_for('transaction.view',
                                                id=transaction.key().id()))

    transaction = Transaction.get(transaction.key())
    self.assertEqual(Transaction.Status.Pending, transaction.status)

    # Ensure that a task is placed in the queue to process the task, and that
    # the parameters are correct.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(transaction.key()), params['transaction_key'])

    # Delete the transaction and attempt to process it.
    transaction.delete()

    # Ensure the error is appropriately logged.
    with mock.patch('logging.error') as error_logger:
      response = self.app.post(task.url, params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

  def test_process_jmd_admin_cash_deposit(self):
    sender = self.create_profile(jmd_balance=5000, is_admin=True)
    recipient = self.create_profile()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Deposit, is_cash_deposit=True)

    params = {'transaction_key': str(transaction.key())}
    response = self.app.post(self.uri_for('transaction.process'), params,
                             headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Ensure balances update correctly, and transaction is marked as
    # completed.
    transaction = Transaction.get(transaction.key())
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(5000, sender.jmd_balance)
    self.assertEqual(2000, recipient.jmd_balance)

    # Ensure the USD balances were not modified.
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  def test_process_usd_admin_cash_deposit(self):
    sender = self.create_profile(usd_balance=5000, is_admin=True)
    recipient = self.create_profile()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        currency=constants.USD_CURRENCY,
        transaction_type=Transaction.Type.Deposit, is_cash_deposit=True)

    params = {'transaction_key': str(transaction.key())}
    response = self.app.post(self.uri_for('transaction.process'), params,
                             headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Ensure balances update correctly, and transaction is marked as
    # completed.
    transaction = Transaction.get(transaction.key())
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(2000, recipient.usd_balance)

    # Ensure the JMD balances were not modified.
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)

  def test_process_jmd_admin_cash_deposit_refund(self):
    sender = self.create_profile(jmd_balance=5000, is_admin=True)
    recipient = self.create_profile(jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Deposit, is_cash_deposit=True,
        status=Transaction.Status.RefundPending)

    params = {'transaction_key': str(transaction.key())}
    response = self.app.post(self.uri_for('transaction.process'), params,
                             headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Ensure balances update correctly, and transaction is marked as
    # completed.
    transaction = Transaction.get(transaction.key())
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(Transaction.Status.Refunded, transaction.status)
    self.assertEqual(5000, sender.jmd_balance)
    self.assertEqual(1000, recipient.jmd_balance)

    # Ensure the USD balances were not modified.
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  def test_process_usd_admin_cash_deposit_refund(self):
    sender = self.create_profile(usd_balance=5000, is_admin=True)
    recipient = self.create_profile(usd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        currency=constants.USD_CURRENCY,
        transaction_type=Transaction.Type.Deposit, is_cash_deposit=True,
        status=Transaction.Status.RefundPending)

    params = {'transaction_key': str(transaction.key())}
    response = self.app.post(self.uri_for('transaction.process'), params,
                             headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Ensure balances update correctly, and transaction is marked as
    # completed.
    transaction = Transaction.get(transaction.key())
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(Transaction.Status.Refunded, transaction.status)
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(1000, recipient.usd_balance)

    # Ensure the JMD balances were not modified.
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)

  def test_process_non_admin_usd_cash_deposit(self):
    sender = self.create_profile(usd_balance=5000)
    recipient = self.create_profile(usd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        currency=constants.USD_CURRENCY,
        transaction_type=Transaction.Type.Deposit, is_cash_deposit=True,
        status=Transaction.Status.RefundPending)

    # Ensure errors are logged.
    with mock.patch('logging.error') as error_logger:
      params = {'transaction_key': str(transaction.key())}
      response = self.app.post(self.uri_for('transaction.process'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Ensure balances are unchanged, and transaction is marked as
    # cancelled.
    transaction = Transaction.get(transaction.key())
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(3000, recipient.usd_balance)

    # Ensure the JMD balances were not modified.
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)

  def test_metrics_task_dispatched_after_successful_transaction(self):
    sender = self.create_profile(jmd_balance=5000)
    recipient = self.create_organization()
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=2000,
        currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    params = {'transaction_key': str(transaction.key())}
    response = self.app.post(self.uri_for('transaction.process'), params,
                             headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Ensure balances update correctly, and transaction is marked as
    # completed.
    transaction = Transaction.get(transaction.key())
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(3000, sender.jmd_balance)
    self.assertEqual(2000, recipient.jmd_balance)

    # Ensure the USD balances were not modified.
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

    # Ensure a task to send the transaction data to keen.io has been created.
    tasks = self.taskqueue_stub.get_filtered_tasks(name=str(transaction.key()))
    self.assertLength(1, tasks)
    task, = tasks

    # Ensure debug logger is called correctly, and that the event is sent to
    # keen.io.
    with mock.patch('logging.debug') as debug_logger:
      with mock.patch('keen.add_event') as keen_add_event:
        deferred.run(task.payload)
        self.assertTrue(keen_add_event.called)
        self.assertEqual(1, keen_add_event.call_count)
        self.assertTrue(debug_logger.called)
        self.assertEqual(2, debug_logger.call_count)
