from google.appengine.api import memcache

import unittest2

from library import testing
from models.transaction import Transaction


class TestHomeHandler(testing.TestCase, unittest2.TestCase):
  def test_home_page_uses_home_template(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('landing.haml')

  def test_home_page_uses_cache(self):
    # Cache should start empty.
    self.assertEqual(0, memcache.get_stats()['items'])

    # After we retrieve the homepage, the cache should be primed.
    response = self.app.get(self.uri_for('home'))
    self.assertEqual(1, memcache.get_stats()['items'])

    # If we get the home page again, we should have a single hit.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertEqual(1, memcache.get_stats()['hits'])

  def test_home_has_join_beta_link(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('a.join-beta[href="%s"]' % (
                                          self.uri_for('signup'))))

  @testing.logged_in
  def test_home_page_displays_first_part_of_users_name(self):
    profile = self.get_current_profile()
    profile.name = 'Super Long Name'
    profile.put()
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertEqual(profile.get_short_name(),
                     response.pyquery('.welcome h3 span').text())

  @testing.logged_in
  def test_home_page_displays_balances(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('h5#usd-balance'))
    self.assertLength(1, response.pyquery('h5#jmd-balance'))

  @testing.logged_in
  def test_home_page_displays_blaze_it_menu(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('.button-actions'))

  @testing.logged_in
  def test_completed_transaction_in_deposits_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              recipient=self.get_current_profile(),
                              status=Transaction.Status.Completed,
                              transaction_type=Transaction.Type.Deposit)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#deposits tr.completed'))

  @testing.logged_in
  def test_pending_transaction_in_deposits_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              recipient=self.get_current_profile(),
                              status=Transaction.Status.Pending,
                              transaction_type=Transaction.Type.Deposit)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#deposits tr.pending'))

  @testing.logged_in
  def test_cancelled_transaction_in_deposits_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              recipient=self.get_current_profile(),
                              status=Transaction.Status.Cancelled,
                              transaction_type=Transaction.Type.Deposit)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#deposits tr.cancelled'))

  @testing.logged_in
  def test_processing_transaction_in_deposits_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              recipient=self.get_current_profile(),
                              status=Transaction.Status.Processing,
                              transaction_type=Transaction.Type.Deposit)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#deposits tr.processing'))

  @testing.logged_in
  def test_completed_transaction_in_outflow_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              sender=self.get_current_profile(),
                              status=Transaction.Status.Completed,
                              transaction_type=Transaction.Type.Transfer)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transactions-sent tr.completed'))

  @testing.logged_in
  def test_pending_transaction_in_outflow_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              sender=self.get_current_profile(),
                              status=Transaction.Status.Pending,
                              transaction_type=Transaction.Type.Transfer)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transactions-sent tr.pending'))

  @testing.logged_in
  def test_cancelled_transaction_in_outflow_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              sender=self.get_current_profile(),
                              status=Transaction.Status.Cancelled,
                              transaction_type=Transaction.Type.Transfer)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transactions-sent tr.cancelled'))

  @testing.logged_in
  def test_processing_transaction_in_outflow_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              sender=self.get_current_profile(),
                              status=Transaction.Status.Processing,
                              transaction_type=Transaction.Type.Transfer)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1, response.pyquery('#transactions-sent tr.processing'))

  @testing.logged_in
  def test_completed_transaction_in_inflow_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              recipient=self.get_current_profile(),
                              status=Transaction.Status.Completed,
                              transaction_type=Transaction.Type.Transfer)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1,
                      response.pyquery('#transactions-received tr.completed'))

  @testing.logged_in
  def test_pending_transaction_in_inflow_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              recipient=self.get_current_profile(),
                              status=Transaction.Status.Pending,
                              transaction_type=Transaction.Type.Transfer)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1,
                      response.pyquery('#transactions-received tr.pending'))

  @testing.logged_in
  def test_cancelled_transaction_in_inflow_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              recipient=self.get_current_profile(),
                              status=Transaction.Status.Cancelled,
                              transaction_type=Transaction.Type.Transfer)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1,
                      response.pyquery('#transactions-received tr.cancelled'))

  @testing.logged_in
  def test_processing_transaction_in_inflow_table_on_home_page(self):
    transaction = Transaction(amount=1000,
                              recipient=self.get_current_profile(),
                              status=Transaction.Status.Processing,
                              transaction_type=Transaction.Type.Transfer)
    transaction.put()

    # Load the dashboard.
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')

    # Checking if transaction loads correctly in the table.
    self.assertLength(1,
                      response.pyquery('#transactions-received tr.processing'))

  @testing.logged_in
  def test_outflow_table_displays_empty_message(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')
    self.assertLength(0, response.pyquery('#transactions-sent table'))
    self.assertLength(1, response.pyquery('#transactions-sent'))
    self.assertLength(1, response.pyquery('#transactions-sent .empty'))

  @testing.logged_in
  def test_inflow_table_displays_empty_message(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')
    self.assertLength(0, response.pyquery('#transactions-received table'))
    self.assertLength(1, response.pyquery('#transactions-received'))
    self.assertLength(1, response.pyquery('#transactions-received .empty'))

  @testing.logged_in
  def test_deposits_table_displays_empty_message(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')
    self.assertLength(0, response.pyquery('#deposits table'))
    self.assertLength(1, response.pyquery('#deposits'))
    self.assertLength(1, response.pyquery('#deposits .empty'))

  @testing.logged_in
  def test_tranasction_sent_has_a_qr_code_modal(self):
    self.create_transaction(
        sender=self.get_current_profile(),
        transaction_type=Transaction.Type.Purchase)
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')
    self.assertLength(1, response.pyquery('.modal.transaction-qr'))

  @testing.logged_in
  def test_transaction_received_has_no_qr_code_modal(self):
    self.create_transaction(
        recipient=self.get_current_profile(),
        transaction_type=Transaction.Type.Transfer)
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')
    self.assertLength(0, response.pyquery('.modal.transaction-qr'))

  @testing.logged_in
  def test_deposit_has_no_qr_code_modal(self):
    self.create_transaction(
        recipient=self.get_current_profile(),
        transaction_type=Transaction.Type.Deposit)
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('home.haml')
    self.assertLength(0, response.pyquery('.modal.transaction-qr'))
