import unittest2

from library import testing


class TestStaffLogout(testing.TestCase, unittest2.TestCase):

  def test_staff_logout_not_logged_in(self):
    self.assertNotStaffLoggedIn()
    response = self.app.get(self.uri_for('staff.logout'))
    staff_login_url = self.uri_for(
        'staff.login', redirect=self.uri_for('staff.logout'))
    self.assertRedirects(response, staff_login_url)
    self.assertNotStaffLoggedIn()

  @testing.logged_in
  def test_staff_logout_logged_in_as_profile(self):
    self.assertNotStaffLoggedIn()
    response = self.app.get(self.uri_for('staff.logout'))
    staff_login_url = self.uri_for(
        'staff.login', redirect=self.uri_for('staff.logout'))
    self.assertRedirects(response, staff_login_url)
    self.assertNotStaffLoggedIn()

  @testing.staff_logged_in
  def test_staff_logout_logged_in_as_staff(self):
    self.assertStaffLoggedIn()
    response = self.app.get(self.uri_for('staff.logout'))
    self.assertRedirects(response, self.uri_for('home'))
    self.assertNotStaffLoggedIn()

  @testing.staff_logged_in
  @testing.logged_in
  def test_staff_logout_logged_in_as_staff_and_profile(self):
    self.assertStaffLoggedIn()
    self.assertLoggedIn()
    response = self.app.get(self.uri_for('staff.logout'))
    self.assertRedirects(response, self.uri_for('home'))
    self.assertNotStaffLoggedIn()
    self.assertLoggedIn()
