import unittest2

from babel.dates import format_datetime

from library import constants
from library import testing
from models.transaction import Transaction


class TestTransactionView(testing.TestCase, unittest2.TestCase):

  @testing.logged_in
  def test_sender_can_view_transaction_by_id(self):
    sender = self.get_current_profile()
    recipient = self.create_profile()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Transfer)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')
    self.assertLength(1, response.pyquery('img.qr-code'))

  @testing.logged_in
  def test_profile_recipient_can_view_transaction_by_id(self):
    sender = self.create_profile()
    recipient = self.get_current_profile()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Transfer)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')
    self.assertLength(0, response.pyquery('img.qr-code'))

  def test_view_transaction_by_id_logged_out(self):
    sender = self.create_profile()
    recipient = self.create_profile()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Transfer)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    login_url = self.uri_for(
        'login', redirect=self.uri_for('transaction.view',
                                       id=transaction.key().id()))
    self.assertRedirects(response, login_url)

  @testing.logged_in
  def test_view_transaction_by_id_unauthorized_profile(self):
    sender = self.create_profile()
    recipient = self.create_profile()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Transfer)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertRedirects(response, self.uri_for('home'))
    self.assertFlashMessage(level='error')

  @testing.logged_in
  def test_view_transaction_by_id_organization_recipient(self):
    sender = self.create_profile()
    recipient = self.create_organization(owner=self.get_current_profile())

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')
    self.assertLength(0, response.pyquery('img.qr-code'))

  @testing.logged_in
  def test_transaction_view_displays_right_information_in_table(self):
    sender = self.create_profile()
    recipient = self.create_organization(owner=self.get_current_profile())

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY)
    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')
    table = response.pyquery('table td').text()
    self.assertIn(transaction.sender.name, table)
    self.assertIn(transaction.recipient.name, table)
    self.assertIn(format_datetime(transaction.created), table)
    self.assertIn(transaction.get_transaction_amount(), table)
    self.assertIn(transaction.status, response.pyquery('#status').text())

  @testing.logged_in
  def test_owner_can_view_transaction_verify(self):
    sender = self.create_profile()
    recipient = self.create_organization(owner=self.get_current_profile())

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY, status=Transaction.Status.Completed)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)

  def test_authorized_staff_member_cannot_view_transaction_by_id(self):
    # Set up recipient organization for transaction.
    organization = self.create_organization()

    # Create a staff account belonging to the organization.
    staff = self.create_staff(organization=organization)
    login = '%s@%s' % (staff.username, organization.identifier)
    self.staff_login(login, self.DEFAULT_PASSWORD)
    self.assertStaffLoggedIn()

    # Make and store transaction.
    transaction = self.create_transaction(
        amount=1000, recipient=organization,
        status=Transaction.Status.Completed,
        transaction_type=Transaction.Type.Purchase)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    login_url = self.uri_for('login',
                             redirect=self.uri_for('transaction.view',
                                                   id=transaction.key().id()))
    self.assertRedirects(response, login_url)

  @testing.logged_in
  def test_sender_cannot_view_transaction_verify(self):
    sender = self.get_current_profile()
    recipient = self.create_organization(owner=self.create_profile())

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY, status=Transaction.Status.Completed)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertLength(0, response.pyquery('#staff-form'))
    self.assertLength(0, response.pyquery('#verify-button'))

  @testing.logged_in
  def test_qr_code_displays_after_transaction_verified(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Completed, sender=self.get_current_profile(),
        verifier=self.create_profile())
    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('h2.verified'))
    self.assertLength(1, response.pyquery('img.qr-code'))

  @testing.logged_in
  def test_completed_transaction_in_transaction_view_page(self):
    sender = self.get_current_profile()
    recipient = self.create_profile()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Completed)

    # Load the transaction view.
    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transaction tr.completed'))

  @testing.logged_in
  def test_pending_transaction_in_transaction_view_page(self):
    sender = self.get_current_profile()
    recipient = self.create_profile()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Pending)

    # Load the transaction view.
    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transaction tr.pending'))

  @testing.logged_in
  def test_cancelled_transaction_in_transaction_view_page(self):
    sender = self.get_current_profile()
    recipient = self.create_profile()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Cancelled)

    # Load the transaction view.
    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transaction tr.cancelled'))

  @testing.logged_in
  def test_processing_transaction_in_transaction_view_page(self):
    sender = self.get_current_profile()
    recipient = self.create_profile()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Processing)

    # Load the transaction view.
    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transaction tr.processing'))

  @testing.logged_in
  def test_refunding_transaction_in_transaction_view_page(self):
    sender = self.get_current_profile()
    recipient = self.create_organization()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Refunding)

    # Load the transaction view.
    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transaction tr.refunding'))

  @testing.logged_in
  def test_refund_pending_transaction_in_transaction_view_page(self):
    sender = self.get_current_profile()
    recipient = self.create_organization()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.RefundPending)

    # Load the transaction view.
    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transaction tr.refund.pending'))

  @testing.logged_in
  def test_refunded_transaction_in_transaction_view_page(self):
    sender = self.get_current_profile()
    recipient = self.create_organization()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Refunded)

    # Load the transaction view.
    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transaction tr.refunded'))

  @testing.logged_in
  def test_staff_actions_div_hidden_on_transfers(self):
    sender = self.get_current_profile()
    recipient = self.create_profile()

    transaction = self.create_transaction(
        amount=2000, recipient=recipient, sender=sender,
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Completed)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')

    # Ensure div.staff-actions is hidden.
    self.assertLength(0, response.pyquery('.staff-actions'))

  @testing.logged_in
  def test_staff_actions_div_hidden_from_sender(self):
    sender = self.get_current_profile()

    transaction = self.create_transaction(
        amount=2000, sender=sender,
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Completed)

    response = self.app.get(
        self.uri_for('transaction.view', id=transaction.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_view.haml')

    # Ensure div.staff-actions is hidden.
    self.assertLength(0, response.pyquery('.staff-actions'))
