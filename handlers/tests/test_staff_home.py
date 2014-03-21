import unittest2

from library import testing
from models.transaction import Transaction


class TestStaffHomeHandler(testing.TestCase, unittest2.TestCase):

  @testing.staff_logged_in
  def test_home_page_displays_first_part_of_users_name(self):
    staff = self.get_current_staff()
    staff.name = 'Super Long Name'
    staff.put()
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertEqual(staff.get_short_name(),
                     response.pyquery('.welcome h2 span').text())

  @testing.staff_logged_in
  def test_home_page_displays_balances(self):
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('h5#usd-balance'))
    self.assertLength(1, response.pyquery('h5#jmd-balance'))

  @testing.staff_logged_in
  def test_completed_transaction_in_verified_table_on_staff_home_page(self):
    current_staff = self.get_current_staff()
    transaction = self.create_transaction(
        amount=1000, verifier=self.get_current_staff(),
        status=Transaction.Status.Completed,
        transaction_type=Transaction.Type.Purchase,
        recipient=current_staff.get_organization())
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1,
                      response.pyquery('#transactions-verified tr.completed'))

  @testing.staff_logged_in
  def test_pending_transaction_in_verified_table_on_staff_home_page(self):
    current_staff = self.get_current_staff()
    transaction = self.create_transaction(
        amount=1000, verifier=self.get_current_staff(),
        status=Transaction.Status.Pending,
        transaction_type=Transaction.Type.Purchase,
        recipient=current_staff.get_organization())
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1,
                      response.pyquery('#transactions-verified tr.pending'))

  @testing.staff_logged_in
  def test_cancelled_transaction_in_verified_table_on_staff_home_page(self):
    current_staff = self.get_current_staff()
    transaction = self.create_transaction(
        amount=1000, verifier=self.get_current_staff(),
        status=Transaction.Status.Cancelled,
        transaction_type=Transaction.Type.Purchase,
        recipient=current_staff.get_organization())
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertTemplateUsed(
        'components/staff_transactions_verified_table.haml')
    self.assertLength(1,
                      response.pyquery('#transactions-verified tr.cancelled'))

  @testing.staff_logged_in
  def test_processing_transaction_in_verified_table_on_staff_home_page(self):
    current_staff = self.get_current_staff()
    transaction = self.create_transaction(
        amount=1000, verifier=self.get_current_staff(),
        status=Transaction.Status.Processing,
        transaction_type=Transaction.Type.Purchase,
        recipient=current_staff.get_organization())
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1,
                      response.pyquery('#transactions-verified tr.processing'))

  @testing.staff_logged_in
  def test_transaction_of_other_org_not_on_table_of_staff(self):
    other_organization = self.create_organization()
    transaction = self.create_transaction(
        amount=1000, recipient=other_organization,
        status=Transaction.Status.Completed,
        verifier=self.create_staff(organization=other_organization),
        transaction_type=Transaction.Type.Purchase)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(0,
                      response.pyquery('#transactions-verified tr.completed'))

  @testing.staff_logged_in
  def test_verified_table_doesnt_show_if_no_transactions(self):
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_home.haml')
    self.assertLength(1, response.pyquery('#transactions-verified'))
    self.assertLength(0, response.pyquery('#transactions-verified table'))

  @testing.staff_logged_in
  def test_not_organization_transaction_not_on_staff_homepage(self):
    other_organization = self.create_organization(identifier='notyours')
    other_staff = self.create_staff(organization=other_organization)
    transaction = self.create_transaction(
        amount=1000, verifier=other_staff, recipient=other_organization,
        status=Transaction.Status.Completed,
        transaction_type=Transaction.Type.Purchase)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_home.haml')

    # Checking no transactions load in the table.
    self.assertLength(0,
                      response.pyquery('#transactions-verified tr.completed'))

  @testing.staff_logged_in
  def test_other_staff_transaction_not_on_staff_homepage(self):
    current_staff = self.get_current_staff()
    organization = current_staff.get_organization()
    other_staff = self.create_staff(organization=organization)

    transaction = self.create_transaction(
        amount=1000, verifier=other_staff,
        recipient=organization,
        status=Transaction.Status.Completed,
        transaction_type=Transaction.Type.Purchase)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_home.haml')

    # Checking no transactions load in the table.
    self.assertLength(0,
                      response.pyquery('#transactions-verified tr.completed'))
