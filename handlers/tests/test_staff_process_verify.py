import mock
import unittest2

from library import constants, testing
from models.staff import Staff
from models.transaction import Transaction


class TestStaffProcessVerify(testing.TestCase, unittest2.TestCase):

  def test_staff_process_verify(self):
    organization = self.create_organization()
    staff = self.create_staff(organization=organization)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        recipient=organization, tip_amount=300,
        currency=constants.JMD_CURRENCY,
        status=Transaction.Status.Completed)

    # Attempt to verify the transaction.
    params = {'transaction_key': str(transaction.key()),
              'verifier_key': str(staff.key())}

    # Emulate the high-replication datastore.
    with self.datastore_consistency_policy(testing.HR_LOW_CONSISTENCY_POLICY):
      response = self.app.post(self.uri_for('staff.process_verify'), params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Refresh the transaction and staff member, and ensure the verifier was set
    # correctly, and the relevant tips have been transferred.
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())
    self.assertIsNotNone(transaction.verifier)
    self.assertIsNotNone(transaction.verified_time)
    self.assertEqual(staff.key(), transaction.verifier.key())
    self.assertEqual(300, staff.jmd_tip_balance)
    self.assertEqual(0, staff.usd_tip_balance)

  def test_staff_process_verify_no_data(self):
    with mock.patch('logging.error') as error_logger:
      response = self.app.post(
          self.uri_for('staff.process_verify'), headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)
      error_logger.assert_called_with(Transaction.Errors.EmptyTransactionKey)

  def test_staff_process_verify_outside_task_queue(self):
    organization = self.create_organization()
    staff = self.create_staff(organization=organization)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        recipient=organization, tip_amount=300,
        currency=constants.JMD_CURRENCY,
        status=Transaction.Status.Completed)

    # Attempt to verify the transaction.
    params = {'transaction_key': str(transaction.key()),
              'verifier_key': str(staff.key())}
    with mock.patch('logging.error') as error_logger:
      response = self.app.post(self.uri_for('staff.process_verify'), params)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)
      error_logger.assert_called_with(Transaction.Errors.UnauthorizedRequest)

  def test_verifying_verified_transaction_fails(self):
    organization = self.create_organization()
    staff1 = self.create_staff(
        username='staff1@example', organization=organization)
    staff2 = self.create_staff(
        username='staff2@example', organization=organization)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Completed,
        verifier=staff1, tip_amount=300, recipient=organization)
    params = {'transaction_key': str(transaction.key()),
              'verifier_key': str(staff2.key())}

    # Ensure error is logged.
    with mock.patch('logging.error') as error_logger:
      response = self.app.post(self.uri_for('staff.process_verify'), params)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Reload transaction and staff, and ensure the verifier has not changed,
    # and the tip amount has not been added to the staff member's tip balance.
    transaction = Transaction.get(transaction.key())
    staff2 = Staff.get(staff2.key())
    self.assertEqual(staff1.key(), transaction.verifier.key())
    self.assertEqual(0, staff2.jmd_tip_balance)
    self.assertEqual(0, staff2.usd_tip_balance)

  def test_verifying_transfer_transaction_fails(self):
    transaction = self.create_transaction(
        status=Transaction.Status.Completed,
        transaction_type=Transaction.Type.Transfer)
    staff = self.create_staff(username='test@example')
    params = {'transaction_key': str(transaction.key()),
              'verifier_key': str(staff.key())}

    # Ensure error is logged.
    with mock.patch('logging.error') as error_logger:
      response = self.app.post(self.uri_for('staff.process_verify'), params)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Reload transaction and staff and ensure that the verifier has not been
    # set, and the staff member's tip balance has not been updated.
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())
    self.assertIsNone(transaction.verifier)
    self.assertEqual(0, staff.jmd_tip_balance)
    self.assertEqual(0, staff.usd_tip_balance)

  def test_verifying_pending_transaction_fails(self):
    organization = self.create_organization()
    staff = self.create_staff(organization=organization)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        recipient=organization, tip_amount=300,
        currency=constants.JMD_CURRENCY,
        status=Transaction.Status.Completed)

    staff = self.create_staff(username='test@example')
    params = {'transaction_key': str(transaction.key()),
              'verifier_key': str(staff.key())}

    # Ensure error is logged.
    with mock.patch('logging.error') as error_logger:
      response = self.app.post(self.uri_for('staff.process_verify'), params)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Reload transaction and staff and ensure that the verifier has not been
    # set, and the staff member's tip balance has not been updated.
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())
    self.assertIsNone(transaction.verifier)
    self.assertEqual(0, staff.jmd_tip_balance)
    self.assertEqual(0, staff.usd_tip_balance)

  def test_unauthorized_staff_cannot_verify_transaction(self):
    organization = self.create_organization()
    staff = self.create_staff(username='test@example')
    self.assertFalse(organization.is_viewable_by(staff))
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        recipient=organization, tip_amount=300,
        currency=constants.JMD_CURRENCY,
        status=Transaction.Status.Completed)

    staff = self.create_staff(username='test@example')
    params = {'transaction_key': str(transaction.key()),
              'verifier_key': str(staff.key())}

    # Ensure error is logged.
    with mock.patch('logging.error') as error_logger:
      response = self.app.post(self.uri_for('staff.process_verify'), params)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Reload transaction and staff, and ensure the verifier has not changed,
    # and the tip amount has not been added to the staff member's tip balance.
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())
    self.assertIsNone(transaction.verifier)
    self.assertEqual(0, staff.jmd_tip_balance)
    self.assertEqual(0, staff.usd_tip_balance)
