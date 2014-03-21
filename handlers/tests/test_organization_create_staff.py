import unittest2

from forms import error_messages
from library import testing
from models.organization import Organization
from models.staff import Staff


class TestCreateStaffHandler(testing.TestCase, unittest2.TestCase):

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_add_staff(self):
    organization = self.get_current_staff().get_organization()

    params = {'name': self.DEFAULT_STAFF_NAME,
              'username': 'username'}
    response = self.app.post(self.uri_for('organization.create_staff',
                                          id=organization.key().id()), params)
    self.assertRedirects(response, self.uri_for('organization.view',
                                                id=organization.key().id()))
    self.assertFlashMessage(message='Successfully added staff.')

    # Reload the organization.
    organization = Organization.get(organization.key())
    self.assertLength(2, organization.get_staff())
    staff = organization.get_staff()[1]
    self.assertEqual(self.DEFAULT_STAFF_NAME, staff.name)
    self.assertEqual('username', staff.username)

    # Check if staff login is correct.
    login = "%s@%s" % (staff.username, organization.identifier)
    self.assertEqual(
        'username@%s' % (self.DEFAULT_ORGANIZATION_IDENTIFIER), login)

    # Check if the staff's initial password is their login.
    self.assertTrue(staff.check_password(login))

    # Log out and ensure newly made staff can log in.
    self.staff_logout()
    response = self.app.get(self.uri_for('staff.login'))
    self.assertOk(response)
    form = response.forms['login-form']

    form['username'] = login
    form['password'] = login
    response = form.submit()
    self.assertRedirects(response, self.uri_for('staff.home'))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_add_staff_with_long_name(self):
    organization = self.get_current_staff().get_organization()

    params = {'name': 'a' * 40, 'username': self.DEFAULT_USERNAME}
    response = self.app.post(self.uri_for('organization.create_staff',
                                          id=organization.key().id()), params)
    self.assertFlashMessage(level='error', response=response,
                            message=error_messages.STAFF_NAME_TOO_LONG)

    # Reload the organization.
    organization = Organization.get_by_id(organization.key().id())
    staff = organization.get_staff()
    self.assertLength(1, staff)

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_add_staff_with_long_username(self):
    organization = self.get_current_staff().get_organization()

    params = {'name': self.DEFAULT_STAFF_NAME, 'username': 'a' * 30}
    response = self.app.post(self.uri_for('organization.create_staff',
                                          id=organization.key().id()), params)
    self.assertFlashMessage(level='error', response=response,
                            message=error_messages.STAFF_USERNAME_TOO_LONG)

    # Reload the organization.
    organization = Organization.get_by_id(organization.key().id())
    staff = organization.get_staff()
    self.assertLength(1, staff)

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_add_staff_with_non_alphanumeric_username(self):
    organization = self.get_current_staff().get_organization()

    params = {'name': self.DEFAULT_STAFF_NAME, 'username': '!@#$%^&*()'}
    response = self.app.post(self.uri_for('organization.create_staff',
                                          id=organization.key().id()), params)
    self.assertFlashMessage(level='error', response=response,
                            message=error_messages.STAFF_ALPHANUMERIC_ONLY)

    # Reload the organization.
    organization = Organization.get_by_id(organization.key().id())
    staff = organization.get_staff()
    self.assertLength(1, staff)

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_add_existing_username_to_organization(self):
    organization = self.get_current_staff().get_organization()
    staff = self.create_staff(username=self.DEFAULT_USERNAME,
                              organization=organization)

    params = {'name': self.DEFAULT_STAFF_NAME,
              'username': self.DEFAULT_USERNAME}
    response = self.app.post(self.uri_for('organization.create_staff',
                                          id=organization.key().id()), params)
    self.assertOk(response)
    self.assertFlashMessage(level='error', response=response,
                            message=error_messages.STAFF_LOGIN_EXISTS)

    # Reload the organization.
    organization = Organization.get_by_id(organization.key().id())
    staff = organization.get_staff()
    self.assertLength(2, staff)

  def test_create_staff_as_logged_out_user(self):
    organization = self.create_organization()
    create_staff_url = self.uri_for('organization.create_staff',
                                    id=organization.key().id())
    response = self.app.post(create_staff_url)
    self.assertRedirects(response, self.uri_for('staff.login',
                                                redirect=create_staff_url))

    # Reload the organization.
    organization = Organization.get_by_id(organization.key().id())
    staff = organization.get_staff()
    self.assertLength(0, staff)

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_create_staff_as_unconcerned_user(self):
    organization = self.create_organization()
    params = {'name': self.DEFAULT_STAFF_NAME,
              'username': self.DEFAULT_USERNAME}
    response = self.app.post(self.uri_for('organization.create_staff',
                                          id=organization.key().id()), params)
    self.assertRedirects(response, self.uri_for('staff.home'))
    self.assertFlashMessage(level='error',
                            message=error_messages.ACCESS_DENIED)

    # Reload the organization.
    organization = Organization.get_by_id(organization.key().id())
    staff = organization.get_staff()
    self.assertLength(0, staff)
