import unittest2

from forms import error_messages
from library import testing
from models.staff import Staff
from models.transaction import Transaction


class TestOrganizationView(testing.TestCase, unittest2.TestCase):

  def test_get_organization_view_page_not_logged_in(self):
    organization = self.create_organization()
    view_url = self.uri_for('organization.view', id=organization.key().id())
    response = self.app.get(view_url)
    self.assertRedirects(
        response, self.uri_for('staff.login', redirect=view_url))

  @testing.staff_logged_in
  def test_get_organization_view_page_logged_in_staff(self):
    organization = self.create_organization()
    view_url = self.uri_for('organization.view', id=organization.key().id())
    response = self.app.get(view_url)
    self.assertRedirects(response, self.uri_for('staff.home'))
    self.assertFlashMessage(level='error',
                            message=error_messages.ACCESS_DENIED)

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_get_organization_view_page_logged_in_admin(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()

    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Ensure page header rendered.
    self.assertLength(1, response.pyquery('#organization-view h2'))

    # Ensure edit organization button leads to the correct link.
    edit_button = response.pyquery('#organization-view .edit-button')
    edit_url = self.uri_for('organization.edit', id=organization.key().id())
    self.assertEqual(edit_url, edit_button.attr('href'))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_only_staff_can_view_organization_page(self):
    organization = self.create_organization()
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertRedirects(response, self.uri_for('staff.home'))
    self.assertFlashMessage(level='error')

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_completed_transaction_in_table_on_organization_page(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()

    # Create a transaction and store it in the database.
    transaction = self.create_transaction(
        recipient=organization, sender=self.create_staff(),
        status=Transaction.Status.Completed, amount=1000,
        transaction_type=Transaction.Type.Purchase)

    # Load the organization's page.
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Checking if the table loads by checking for a .transaction class
    # and that a completed transaction has a completed class.
    self.assertLength(1, response.pyquery('.transaction-section table'))
    self.assertLength(1, response.pyquery('tr.completed'))
    self.assertLength(1, response.pyquery(
        'td.status a[href="%s"]' %
        (self.uri_for('transaction.verify', uuid=transaction.uuid))))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_pending_transaction_in_table_on_organization_page(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()

    # Create a transaction and store it in the database.
    transaction = self.create_transaction(
        recipient=organization, sender=self.create_staff(),
        status=Transaction.Status.Pending, amount=1000,
        transaction_type=Transaction.Type.Purchase)

    # Load the organization's page.
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Checking if the table loads by checking for a .transaction class
    # and that a pending transaction has a pending class.
    self.assertLength(1, response.pyquery('.transaction-section table'))
    self.assertLength(1, response.pyquery('tr.pending'))
    self.assertLength(1, response.pyquery(
        'td.status a[href="%s"]' %
        (self.uri_for('transaction.verify', uuid=transaction.uuid))))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_processing_transaction_in_table_on_organization_page(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()

    # Create a transaction and store it in the database.
    transaction = self.create_transaction(
        recipient=organization, sender=self.create_staff(),
        status=Transaction.Status.Processing, amount=1000,
        transaction_type=Transaction.Type.Purchase)

    # Load the organization's page.
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Checking if the table loads by checking for a .transaction class
    # and that a pending transaction has a pending class.
    self.assertLength(1, response.pyquery('.transaction-section table'))
    self.assertLength(1, response.pyquery('tr.processing'))
    self.assertLength(1, response.pyquery(
        'td.status a[href="%s"]' %
        (self.uri_for('transaction.verify', uuid=transaction.uuid))))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_cancelled_transaction_in_table_on_organization_page(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()

    # Create a transaction and store it in the database.
    transaction = self.create_transaction(
        recipient=organization, sender=self.create_staff(),
        status=Transaction.Status.Cancelled, amount=1000,
        transaction_type=Transaction.Type.Purchase)

    # Load the organization's page.
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Checking if the table loads by checking for a .transaction class
    # and that a cancelled transaction has a cancelled class.
    self.assertLength(1, response.pyquery('.transaction-section table'))
    self.assertLength(1, response.pyquery('tr.cancelled'))
    self.assertLength(1, response.pyquery(
        'td.status a[href="%s"]' %
        (self.uri_for('transaction.verify', uuid=transaction.uuid))))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_refunding_transaction_in_table_on_organization_page(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()

    # Create a transaction and store it in the database.
    transaction = self.create_transaction(
        recipient=organization, sender=self.create_staff(),
        status=Transaction.Status.Refunding, amount=1000,
        transaction_type=Transaction.Type.Purchase)

    # Load the organization's page.
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Checking if the table loads by checking for a .transaction class
    # and that a refunding transaction has a cancelled class.
    self.assertLength(1, response.pyquery('.transaction-section table'))
    self.assertLength(1, response.pyquery('tr.refunding'))
    self.assertLength(1, response.pyquery(
        'td.status a[href="%s"]' %
        (self.uri_for('transaction.verify', uuid=transaction.uuid))))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_refund_pending_transaction_in_table_on_organization_page(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()

    # Create a transaction and store it in the database.
    transaction = self.create_transaction(
        recipient=organization, sender=self.create_staff(),
        status=Transaction.Status.RefundPending, amount=1000,
        transaction_type=Transaction.Type.Purchase)

    # Load the organization's page.
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Checking if the table loads by checking for a .transaction class
    # and that a refund pending transaction has a cancelled class.
    self.assertLength(1, response.pyquery('.transaction-section table'))
    self.assertLength(1, response.pyquery('tr.refund.pending'))
    self.assertLength(1, response.pyquery(
        'td.status a[href="%s"]' %
        (self.uri_for('transaction.verify', uuid=transaction.uuid))))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_refunded_transaction_in_table_on_organization_page(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()

    # Create a transaction and store it in the database.
    transaction = self.create_transaction(
        recipient=organization, sender=self.create_staff(),
        status=Transaction.Status.Refunded, amount=1000,
        transaction_type=Transaction.Type.Purchase)

    # Load the organization's page.
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Checking if the table loads by checking for a .transaction class
    # and that a refunded transaction has a cancelled class.
    self.assertLength(1, response.pyquery('.transaction-section table'))
    self.assertLength(1, response.pyquery('tr.refunded'))
    self.assertLength(1, response.pyquery(
        'td.status a[href="%s"]' %
        (self.uri_for('transaction.verify', uuid=transaction.uuid))))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_no_transactions_received_displays_message(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()

    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Ensure the table shows the empty message.
    self.assertLength(1, response.pyquery('.transaction-section .empty h3'))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_tip_displays_successfully(self):
    # Get the current staff member's Organization.
    organization = self.get_current_staff().get_organization()
    staff = self.create_staff(organization=organization)

    # Create a transaction and store it in the database.
    transaction = self.create_transaction(
        amount=1000, recipient=organization,
        status=Transaction.Status.Completed, tip_amount=200,
        transaction_type=Transaction.Type.Purchase, verifier=staff)

    # Load the organization's page.
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Checking if the table loads by checking for a .transaction class
    # and that a completed transaction has a completed class.
    self.assertLength(1, response.pyquery('.transaction-section table'))
    self.assertLength(1, response.pyquery('tr.completed'))

    # Ensure the transaction verifier is shown.
    verifier = response.pyquery('td[data-title="Verifier"]')
    self.assertLength(1, verifier)
    self.assertIn(staff.name, verifier.html())

    # Ensure the transaction verifier's tip displays correctly.
    tip = response.pyquery('td[data-title="Tip"]')
    self.assertLength(1, tip)
    self.assertIn('%.2f' % (transaction.tip_amount / 100), tip.html())

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_staff_tab_displays_correctly(self):
    # Get the current staff member's Organization.
    staff1 = self.get_current_staff()
    organization = staff1.get_organization()

    staff2 = self.create_staff(name='enabled', username='enabled',
                               organization=organization)
    staff3 = self.create_staff(name='disabled', username='disabled',
                               organization=organization)
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')
    self.assertTemplateUsed('components/organization_staff_tab.haml')

    # Test if forms for creating staff display.
    self.assertLength(1, response.pyquery('input#name'))
    self.assertLength(1, response.pyquery('input#username'))
    self.assertEqual('@%s' % organization.identifier,
                     response.pyquery('.add-on').text())

    # Test if staff members display.
    self.assertEqual(staff1.name,
                     response.pyquery('td.staff-name:eq(0)').text())
    self.assertEqual(
        '%s@%s' % (staff1.username, organization.identifier),
        response.pyquery('td.staff-login:eq(0)').text())

    self.assertEqual(staff2.name,
                     response.pyquery('td.staff-name:eq(1)').text())
    self.assertEqual(
        '%s@%s' % (staff2.username, organization.identifier),
        response.pyquery('td.staff-login:eq(1)').text())

    self.assertEqual(staff3.name,
                     response.pyquery('td.staff-name:eq(2)').text())
    self.assertEqual(
        '%s@%s' % (staff3.username, organization.identifier),
        response.pyquery('td.staff-login:eq(2)').text())

    # Test if form for toggling staff is present.
    self.assertLength(3, response.pyquery('form.toggle-active'))
    self.assertLength(3, response.pyquery('.toggle'))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_transaction_amount_displays_successfully(self):
    # Create an organization for the transaction's recipient.
    organization = self.get_current_staff().get_organization()
    staff = self.create_staff(organization=organization)

    # Create a transaction and store it in the database.
    transaction = self.create_transaction(
        amount=1000, recipient=organization,
        status=Transaction.Status.Completed, tip_amount=200,
        transaction_type=Transaction.Type.Purchase, verifier=staff)

    # Load the organization's page.
    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_view.haml')

    # Checking if the table loads by checking for a .transaction class
    # and that a completed transaction has a completed class.
    self.assertLength(1, response.pyquery('.transaction-section table'))
    self.assertLength(1, response.pyquery('tr.completed'))

    # Ensure the transaction verifier is shown.
    verifier = response.pyquery('td[data-title="Verifier"]')
    self.assertLength(1, verifier)
    self.assertIn(staff.name, verifier.html())

    # Ensure the transaction verifier's total displays correctly.
    total = response.pyquery('td[data-title="Total"]')
    self.assertLength(1, total)
    total_amount = transaction.amount + transaction.tip_amount
    self.assertIn('%.2f' % (total_amount / 100), total.html())
