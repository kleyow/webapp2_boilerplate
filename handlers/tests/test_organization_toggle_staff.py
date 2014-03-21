import unittest2

from forms import error_messages
from library import testing
from models.staff import Staff


class TestToggleStaffHandler(testing.TestCase, unittest2.TestCase):

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_toggle_active_enabled_staff(self):
    organization = self.get_current_staff().get_organization()
    staff = self.create_staff(organization=organization, username='test')

    # Check that the staff is not active.
    self.assertFalse(staff.is_active)

    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    toggle_form = 'toggle-%s' % staff.username
    form = response.forms[toggle_form]
    response = form.submit()
    self.assertRedirects(response, self.uri_for('organization.view',
                                                id=organization.key().id()))
    self.assertFlashMessage(message='Successfully enabled staff.')

    # Reload staff.
    staff = Staff.get(staff.key())

    # Check that the staff is active.
    self.assertTrue(staff.is_active)

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_toggle_active_disabled_staff(self):
    organization = self.get_current_staff().get_organization()
    staff = self.create_staff(organization=organization, is_active=True,
                              username='test')

    # Check that the staff is active.
    self.assertTrue(staff.is_active)

    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    toggle_form = 'toggle-%s' % staff.username
    form = response.forms[toggle_form]
    response = form.submit()
    self.assertRedirects(response, self.uri_for('organization.view',
                                                id=organization.key().id()))
    self.assertFlashMessage(message='Successfully disabled staff.')

    # Reload staff.
    staff = Staff.get(staff.key())

    # Check that the staff is not active.
    self.assertFalse(staff.is_active)

  def test_toggle_staff_is_active_as_logged_out_user(self):
    organization = self.create_organization()
    staff = self.create_staff(organization=organization)

    # Check that the staff is not active.
    self.assertFalse(staff.is_active)
    toggle_staff_url = self.uri_for('organization.toggle_active')
    response = self.app.post(toggle_staff_url)
    self.assertRedirects(response, self.uri_for('staff.login',
                                                redirect=toggle_staff_url))

    # Reload staff.
    staff = Staff.get_by_id(int(staff.key().id()), parent=organization)

    # Check that the staff is still not active.
    self.assertFalse(staff.is_active)

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_toggle_staff_is_active_as_unconcerned_user(self):
    organization = self.create_organization()
    staff = self.create_staff(organization=organization)

    # Check that the staff is not active.
    self.assertFalse(staff.is_active)

    response = self.app.get(self.uri_for('organization.view',
                                         id=organization.key().id()))
    self.assertRedirects(response, self.uri_for('staff.home'))
    self.assertFlashMessage(level='error',
                            message=error_messages.ACCESS_DENIED)

    # Reload staff.
    staff = Staff.get_by_id(int(staff.key().id()), parent=organization)

    # Check that the staff is still not active.
    self.assertFalse(staff.is_active)

  @testing.staff_logged_in
  def test_toggle_staff_is_active_as_staff_member(self):
    staff = self.get_current_staff()
    organization = staff.get_organization()

    # Check that the staff is not active.
    self.assertFalse(staff.is_active)
    toggle_staff_url = self.uri_for('organization.toggle_active')
    login = '%s@%s' % (staff.username, organization.identifier)
    params = {'username': login}
    response = self.app.post(toggle_staff_url, params)
    self.assertRedirects(response, self.uri_for('staff.home'))

    # Reload staff.
    staff = Staff.get(staff.key())

    # Check that the staff is still not active.
    self.assertFalse(staff.is_active)
