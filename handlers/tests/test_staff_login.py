import unittest2

from library import testing
from models.staff import Staff


class TestStaffLogin(testing.TestCase, unittest2.TestCase):

  def test_get_login_not_logged_in(self):
    response = self.app.get(self.uri_for('staff.login'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_login.haml')
    self.assertLength(1, response.pyquery('form#login-form'))

  @testing.logged_in
  def test_get_login_logged_in_as_profile(self):
    response = self.app.get(self.uri_for('staff.login'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_login.haml')
    self.assertLength(1, response.pyquery('form#login-form'))

  @testing.staff_logged_in
  def test_get_login_logged_in_as_staff(self):
    response = self.app.get(self.uri_for('staff.login'))
    self.assertRedirects(response, self.uri_for('staff.home'))

  def test_login_as_staff_member_logged_out(self):
    organization = self.create_organization()
    staff = self.create_staff(organization=organization)
    response = self.app.get(self.uri_for('staff.login'))
    self.assertOk(response)
    self.assertNotStaffLoggedIn()
    form = response.forms['login-form']
    login = '%s@%s' % (staff.username, organization.identifier)
    form['username'] = login
    form['password'] = self.DEFAULT_PASSWORD
    response = form.submit()
    self.assertRedirects(response, self.uri_for('staff.home'))
    self.assertStaffLoggedIn()

  @testing.logged_in
  def test_login_as_staff_member_logged_in_as_profile(self):
    organization = self.create_organization()
    staff = self.create_staff(organization=organization)
    response = self.app.get(self.uri_for('staff.login'))
    self.assertOk(response)
    self.assertLoggedIn()
    self.assertNotStaffLoggedIn()
    form = response.forms['login-form']
    login = '%s@%s' % (staff.username, organization.identifier)
    form['username'] = login
    form['password'] = self.DEFAULT_PASSWORD
    response = form.submit()
    self.assertRedirects(response, self.uri_for('staff.home'))
    self.assertStaffLoggedIn()

  @testing.staff_logged_in
  def test_post_staff_login_already_logged_in(self):
    staff = self.get_current_staff()
    login = '%s@%s' % (staff.username, staff.get_organization().identifier)
    params = {'username': login,
              'password': self.DEFAULT_PASSWORD}
    response = self.app.post(self.uri_for('staff.login'), params)
    self.assertRedirects(response, self.uri_for('staff.home'))
    self.assertStaffLoggedIn()

  def test_login_case_insensitive_field(self):
    self.create_staff(organization=self.create_organization())
    self.assertNotStaffLoggedIn()
    organization = self.create_organization()
    staff = self.create_staff(organization=organization)

    # Attempt to log in with uppercase username.
    login = '%s@%s' % (staff.username, organization.identifier)
    params = {'username': login.upper(),
              'password': self.DEFAULT_PASSWORD}
    response = self.app.post(self.uri_for('staff.login'), params)
    self.assertRedirects(response, self.uri_for('staff.home'))
    self.assertStaffLoggedIn()

  def test_login_nonexisting_account(self):
    username, password = 'not@correct', 'pass'

    # Attempt to log in with invalid credentials.
    params = {'username': username, 'password': password}
    response = self.app.post(self.uri_for('staff.login'), params)
    self.assertOk(response)
    self.assertLength(1, response.pyquery('.login-error'))
    self.assertNotStaffLoggedIn()

  def test_login_incorrect_password(self):
    self.create_staff(organization=self.create_organization())
    params = {'username': 'wrong@example', 'password': 'WRONG'}
    response = self.app.post(self.uri_for('staff.login'), params)
    self.assertOk(response)
    self.assertLength(1, response.pyquery('.login-error'))
    self.assertNotStaffLoggedIn()

  def test_staff_login_nonexistent_organization(self):
    response = self.staff_login()
    self.assertOk(response)
    self.assertLength(1, response.pyquery('.login-error'))
    self.assertNotStaffLoggedIn()

  def test_login_as_staff_member_not_activated(self):
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
    self.assertFlashMessage(message='Please finish your registration with %s.'
                            % staff.get_organization().name, level='info')

  def test_login_as_staff_invalid_login_string(self):
    """Ensure logins without the '@' sign will not cause a 500."""

    response = self.app.get(self.uri_for('staff.login'))
    form = response.forms['login-form']
    form['username'] = 'invalid'
    form['password'] = self.DEFAULT_PASSWORD
    response = form.submit()
    self.assertOk(response)
    self.assertLength(1, response.pyquery('.login-error'))

  def test_login_as_admin_staff_redirects_to_organization_view(self):
    """Ensure admins will be sent to the Organization home upon login."""

    staff = self.create_staff(role=Staff.Role.Admin)
    organization = staff.get_organization()
    response = self.app.get(self.uri_for('staff.login'))
    form = response.forms['login-form']
    staff_username = '%s@%s' % (staff.username, organization.identifier)
    form['username'] = staff_username
    form['password'] = self.DEFAULT_PASSWORD
    response = form.submit()
    organization_home = self.uri_for(
        'organization.view', id=organization.key().id())
    self.assertRedirects(response, organization_home)

  def test_login_as_manager_staff_redirects_to_organization_view(self):
    """Ensure managers will be sent to the Organization home upon login."""

    staff = self.create_staff(role=Staff.Role.Manager)
    organization = staff.get_organization()
    response = self.app.get(self.uri_for('staff.login'))
    form = response.forms['login-form']
    staff_username = '%s@%s' % (staff.username, organization.identifier)
    form['username'] = staff_username
    form['password'] = self.DEFAULT_PASSWORD
    response = form.submit()
    organization_home = self.uri_for(
        'organization.view', id=organization.key().id())
    self.assertRedirects(response, organization_home)

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_post_admin_staff_login_already_logged_in(self):
    """Ensure logged in admins are redirected to organization home."""

    staff = self.get_current_staff()
    organization = staff.get_organization()
    response = self.app.get(self.uri_for('staff.login'))
    organization_home = self.uri_for(
        'organization.view', id=organization.key().id())
    self.assertRedirects(response, organization_home)

  @testing.login_as_staff(role=Staff.Role.Manager)
  def test_post_manager_staff_login_already_logged_in(self):
    """Ensure logged in managers are redirected to organization home."""

    staff = self.get_current_staff()
    organization = staff.get_organization()
    response = self.app.get(self.uri_for('staff.login'))
    organization_home = self.uri_for(
        'organization.view', id=organization.key().id())
    self.assertRedirects(response, organization_home)
