import unittest2

from library import constants, testing
from models.transaction import Transaction


class TestAdminHistory(testing.TestCase, unittest2.TestCase):

  def test_get_admin_history_not_logged_in(self):
    response = self.app.get(self.uri_for('admin.history'))
    login_url = self.uri_for('login', redirect=self.uri_for('admin.history'))
    self.assertRedirects(response, login_url)

  @testing.logged_in
  def test_get_admin_history_not_admin(self):
    response = self.app.get(self.uri_for('admin.history'))
    self.assertRedirects(response, self.uri_for('home'))

  @testing.staff_logged_in
  def test_get_admin_history_staff(self):
    response = self.app.get(self.uri_for('admin.history'))
    login_url = self.uri_for('login', redirect=self.uri_for('admin.history'))
    self.assertRedirects(response, login_url)

  @testing.login_as(is_admin=True)
  def test_get_admin_history_no_transactions(self):
    response = self.app.get(self.uri_for('admin.history'))
    self.assertOk(response)
    self.assertTemplateUsed('admin/history.haml')
    self.assertLength(1, response.pyquery('table#totals'))
    self.assertLength(0, response.pyquery('table#transactions'))
    self.assertEqual(
        '$ 0.00', response.pyquery('td[data-title="USD Total"]').text())
    self.assertEqual(
        '$ 0.00', response.pyquery('td[data-title="JMD Total"]').text())

  @testing.login_as(is_admin=True)
  def test_get_admin_history_with_transactions_jmd(self):
    current_profile = self.get_current_profile()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit, sender=current_profile,
        status=Transaction.Status.Completed, amount=3000,
        currency=constants.JMD_CURRENCY)
    response = self.app.get(self.uri_for('admin.history'))
    self.assertOk(response)
    self.assertTemplateUsed('admin/history.haml')
    self.assertLength(1, response.pyquery('table#totals'))
    self.assertLength(1, response.pyquery('table#transactions'))
    self.assertLength(1, response.pyquery('tr.completed'))
    self.assertEqual(transaction.get_transaction_amount(),
                     response.pyquery('td[data-title="Amount"]').text())
    amount_text = '$ %.2f' % (transaction.amount / 100)
    self.assertEqual(
        amount_text, response.pyquery('td[data-title="JMD Total"]').text())
    self.assertEqual(
        '$ 0.00', response.pyquery('td[data-title="USD Total"]').text())

  @testing.login_as(is_admin=True)
  def test_get_admin_history_with_transactions_usd(self):
    current_profile = self.get_current_profile()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit, sender=current_profile,
        status=Transaction.Status.Completed, amount=3000,
        currency=constants.USD_CURRENCY)
    response = self.app.get(self.uri_for('admin.history'))
    self.assertOk(response)
    self.assertTemplateUsed('admin/history.haml')
    self.assertLength(1, response.pyquery('table#totals'))
    self.assertLength(1, response.pyquery('table#transactions'))
    self.assertLength(1, response.pyquery('tr.completed'))
    self.assertEqual(transaction.get_transaction_amount(),
                     response.pyquery('td[data-title="Amount"]').text())
    amount_text = '$ %.2f' % (transaction.amount / 100)
    self.assertEqual(
        amount_text, response.pyquery('td[data-title="USD Total"]').text())
    self.assertEqual(
        '$ 0.00', response.pyquery('td[data-title="JMD Total"]').text())
