import unittest2

from library import testing


class TestSignupHandler(testing.TestCase, unittest2.TestCase):
  UPDATE_DATA = {'password': 'pass', 'pin': '1234'}

  @testing.staff_logged_in
  def test_update(self):
    response = self.app.get(self.uri_for('staff.update'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_update.haml')

  @testing.staff_logged_in
  def test_update_inputs_have_proper_types(self):
    # We rely on some client-side browser-built-in validation with fields,
    # so we should check that we don't accidentally change an email field
    # to a text field.
    response = self.app.get(self.uri_for('staff.update'))

    password_field = response.pyquery('input#password')
    self.assertLength(1, password_field)
    self.assertEqual('password', password_field.attr['type'])
    self.assertEqual('password', password_field.attr['name'])
    self.assertIsNotNone(password_field.attr['required'])

    pin_field = response.pyquery('input#pin')
    self.assertLength(1, pin_field)
    self.assertEqual('password', pin_field.attr['type'])
    self.assertEqual('pin', pin_field.attr['name'])
    self.assertIsNotNone(pin_field.attr['required'])

  @testing.staff_logged_in
  def test_password_not_submitted(self):
    response = self.app.get(self.uri_for('staff.update'))
    form = response.forms['staff-update-form']
    form['password'] = ''
    response = form.submit()
    self.assertFlashMessage(level='error', response=response)

    self.staff_logout()
    response = self.staff_login(password=self.UPDATE_DATA['password'])
    self.assertOk(response, self.uri_for('staff.login'))
    response = self.staff_login()
    self.assertRedirects(response, self.uri_for('staff.home'))

  @testing.staff_logged_in
  def test_pin_not_submitted(self):
    response = self.app.get(self.uri_for('staff.update'))
    form = response.forms['staff-update-form']
    form['pin'] = ''
    response = form.submit()
    self.assertFlashMessage(level='error', response=response)

  def test_update_page_flow(self):
    organization = self.create_organization()
    staff = self.create_staff(organization=organization)
    staff.pin = None
    staff.put()
    self.assertIsNone(staff.pin)

    response = self.app.get(self.uri_for('staff.login'))
    self.assertOk(response)
    self.assertNotStaffLoggedIn()
    form = response.forms['login-form']
    form['username'] = self.DEFAULT_STAFF_LOGIN
    form['password'] = self.DEFAULT_PASSWORD
    response = form.submit()
    self.assertRedirects(response, self.uri_for('staff.home'))
    response = self.app.get(self.uri_for('staff.home'))
    self.assertRedirects(response, self.uri_for('staff.update'))
    response = self.app.get(self.uri_for('staff.update'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_update.haml')

    # Check that things are set to default.
    self.assertEqual(self.DEFAULT_USERNAME, staff.username)
    self.assertFalse(staff.is_active)
    self.assertFalse(staff.is_activated())

    # Finish up registration with the form.
    response = self.app.get(self.uri_for('staff.update'))
    form = response.forms['staff-update-form']
    form['password'] = self.UPDATE_DATA['password']
    form['pin'] = self.UPDATE_DATA['pin']
    response = form.submit()
    self.assertRedirects(response, self.uri_for('staff.home'))

    self.staff_logout()

    # Login with new password.
    self.staff_login(login=self.DEFAULT_STAFF_LOGIN,
                     password=self.UPDATE_DATA['password'])

    self.assertStaffLoggedIn()
