import unittest2

from forms import error_messages
from library import constants, testing

from models.staff import Staff
from models.transaction import Transaction


class TestStaffVerify(testing.TestCase, unittest2.TestCase):

  def test_verify_transaction_logged_out(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Completed)

    params = {'uuid': transaction.uuid}
    response = self.app.post(self.uri_for('staff.verify'), params)
    staff_login_url = self.uri_for(
        'staff.login', redirect=self.uri_for('staff.verify'))
    self.assertRedirects(response, staff_login_url)

    # Reload the transaction and ensure the verifier has not been set.
    transaction = Transaction.get(transaction.key())
    self.assertIsNone(transaction.verifier)

  @testing.staff_logged_in
  def test_non_staff_member_cannot_verify_transactions(self):
    sender = self.create_profile()
    recipient = self.create_organization()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY, status=Transaction.Status.Completed)

    params = {'uuid': transaction.uuid}
    response = self.app.post(self.uri_for('staff.verify'), params)
    self.assertRedirects(
        response, self.uri_for('transaction.verify', uuid=transaction.uuid))
    self.assertFlashMessage(
        message=error_messages.UNAUTHORIZED_VERIFICATION, level='error')

    # Reload the transaction and ensure the verifier has been set.
    transaction = Transaction.get(transaction.key())
    self.assertIsNone(transaction.verifier)

  def test_staff_verify_flow(self):
    sender = self.create_profile()
    recipient = self.create_organization()
    staff = self.create_staff(organization=recipient)

    # Login as staff and view the transaction.
    login = '%s@%s' % (staff.username, recipient.identifier)
    self.staff_login(login, self.DEFAULT_PASSWORD)
    self.assertStaffLoggedIn()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY, status=Transaction.Status.Completed,
        tip_amount=300)

    response = self.app.get(
        self.uri_for('transaction.verify', uuid=transaction.uuid))
    self.assertOk(response)

    form = response.forms['staff-form']
    form['uuid'] = transaction.uuid
    response = form.submit()
    receipt_url = self.uri_for('transaction.verify', uuid=transaction.uuid)
    self.assertRedirects(response, receipt_url)
    self.assertFlashMessage(level='success')

    # Reload the transaction and verifier and ensure the verifier has been set
    # correctly, and that their tip balance has been incremented.
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())
    self.assertIsNotNone(transaction.verifier)
    self.assertEqual(staff.key(), transaction.verifier.key())
    self.assertEqual(300, staff.usd_tip_balance)

  def test_staff_member_can_verify_transaction(self):
    sender = self.create_profile()
    recipient = self.create_organization()
    staff = self.create_staff(organization=recipient)

    # Login as staff and view the transaction.
    login = '%s@%s' % (staff.username, recipient.identifier)
    self.staff_login(login, self.DEFAULT_PASSWORD)
    self.assertStaffLoggedIn()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY, status=Transaction.Status.Completed,
        tip_amount=300)

    params = {'uuid': transaction.uuid}
    response = self.app.post(self.uri_for('staff.verify'), params)
    receipt_url = self.uri_for('transaction.verify', uuid=transaction.uuid)
    self.assertRedirects(response, receipt_url)
    self.assertFlashMessage(level='success')

    # Reload the transaction and verifier and ensure the verifier has been set
    # correctly, and that their tip balance has been incremented.
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())
    self.assertIsNotNone(transaction.verifier)
    self.assertEqual(staff.key(), transaction.verifier.key())
    self.assertEqual(300, staff.usd_tip_balance)

  @testing.staff_logged_in
  def test_verify_nonexistent_transaction(self):
    params = {'uuid': 'NOT_A_UUID'}
    response = self.app.post(self.uri_for('staff.verify'), params,
                             status=404)
    self.assertNotFound(response)

  @testing.staff_logged_in
  def test_blank_uuid(self):
    params = {'uuid', ''}
    response = self.app.post(self.uri_for('staff.verify'), params,
                             status=404)
    self.assertNotFound(response)

  @testing.logged_in
  def test_sender_cannot_verify_transaction(self):
    sender = self.get_current_profile()
    recipient = self.create_organization()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY, status=Transaction.Status.Completed)

    params = {'uuid': transaction.uuid}
    response = self.app.post(self.uri_for('staff.verify'), params)
    staff_login_url = self.uri_for(
        'staff.login', redirect=self.uri_for('staff.verify'))
    self.assertRedirects(response, staff_login_url)

  def test_transactions_cannot_be_verified_twice(self):
    sender = self.create_profile()
    recipient = self.create_organization()
    staff1 = self.create_staff(organization=recipient)
    staff2 = self.create_staff(organization=recipient)

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY, verifier=staff1,
        status=Transaction.Status.Completed)

    # Login as staff and view the transaction.
    login = '%s@%s' % (staff2.username, recipient.identifier)
    self.staff_login(login, self.DEFAULT_PASSWORD)
    self.assertStaffLoggedIn()

    params = {'uuid': transaction.uuid}
    response = self.app.post(self.uri_for('staff.verify'), params)
    self.assertRedirects(
        response, self.uri_for('transaction.verify', uuid=transaction.uuid))
    self.assertFlashMessage(message=error_messages.ALREADY_VERIFIED,
                            level='error')

    # Reload the transaction and verifier and ensure the verifier has been set
    # correctly, and that their tip balance has not changed.
    transaction = Transaction.get(transaction.key())
    staff2 = Staff.get(staff2.key())
    self.assertIsNotNone(transaction.verifier)
    self.assertEqual(staff1.key(), transaction.verifier.key())
    self.assertEqual(0, staff2.usd_tip_balance)
    self.assertEqual(0, staff2.jmd_tip_balance)

  def test_transfers_cannot_be_verified(self):
    staff = self.create_staff()

    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer,
        currency=constants.USD_CURRENCY,
        status=Transaction.Status.Completed)

    # Login as staff and view the transaction.
    login = '%s@%s' % (staff.username, staff.get_organization().identifier)
    self.staff_login(login, self.DEFAULT_PASSWORD)
    self.assertStaffLoggedIn()

    params = {'uuid': transaction.uuid}
    response = self.app.post(self.uri_for('staff.verify'), params)
    self.assertRedirects(
        response, self.uri_for('transaction.verify', uuid=transaction.uuid))
    self.assertFlashMessage(message=error_messages.PURCHASES_ONLY_VERIFIABLE,
                            level='error')

    # Reload the transaction and verifier and ensure the verifier has not been
    # set, and that their tip balance has not changed.
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertEqual(0, staff.usd_tip_balance)
    self.assertEqual(0, staff.jmd_tip_balance)

  def test_deposits_cannot_be_verified(self):
    staff = self.create_staff()

    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit,
        currency=constants.USD_CURRENCY,
        status=Transaction.Status.Completed)

    # Login as staff and view the transaction.
    login = '%s@%s' % (staff.username, staff.get_organization().identifier)
    self.staff_login(login, self.DEFAULT_PASSWORD)
    self.assertStaffLoggedIn()

    params = {'uuid': transaction.uuid}
    response = self.app.post(self.uri_for('staff.verify'), params)
    self.assertRedirects(
        response, self.uri_for('transaction.verify', uuid=transaction.uuid))
    self.assertFlashMessage(message=error_messages.PURCHASES_ONLY_VERIFIABLE,
                            level='error')

    # Reload the transaction and verifier and ensure the verifier has not been
    # set, and that their tip balance has not changed.
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertEqual(0, staff.usd_tip_balance)
    self.assertEqual(0, staff.jmd_tip_balance)
