import unittest2

from library import testing


class TestNavbar(testing.TestCase, unittest2.TestCase):

  @testing.logged_in
  def test_navbar_rendered_on_dashboard(self):
    response = self.app.get(self.uri_for('home'))
    self.assertTemplateUsed('private_base.haml',
                            'components/navbar_private.haml')
    self.assertLength(1, response.pyquery('div.navbar'))

  @testing.logged_in
  def test_private_navbar_always_rendered_when_logged_in(self):
    response = self.app.get(self.uri_for('contact'))
    self.assertTemplateUsed('public_base.haml',
                            'components/navbar_private.haml')
    self.assertLength(1, response.pyquery('div.navbar'))

  def test_public_navbar_rendered_when_not_logged_in(self):
    response = self.app.get(self.uri_for('home'))
    self.assertTemplateUsed('public_base.haml',
                            'components/navbar_public.haml')
    self.assertLength(1, response.pyquery('div.navbar'))

  @testing.login_as(is_admin=True)
  def test_admin_links_displayed_to_admins(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertTemplateUsed('components/navbar_private.haml')
    add_organization_link = ('a[href="%s"]' %
                             self.uri_for('admin.add_organization'))
    deposit_link = ('a[href="%s"]' % self.uri_for('admin.deposit'))
    history_link = ('a[href="%s"]' % self.uri_for('admin.history'))

    self.assertLength(1, response.pyquery(add_organization_link))
    self.assertLength(1, response.pyquery(deposit_link))
    self.assertLength(1, response.pyquery(history_link))

  @testing.logged_in
  def test_admin_links_not_displayed_to_non_admins(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    add_organization_link = ('a[href="%s"]' %
                             self.uri_for('admin.add_organization'))
    deposit_link = ('a[href="%s"]' % self.uri_for('admin.deposit'))
    history_link = ('a[href="%s"]' % self.uri_for('admin.history'))

    self.assertLength(0, response.pyquery(add_organization_link))
    self.assertLength(0, response.pyquery(deposit_link))
    self.assertLength(0, response.pyquery(history_link))

  def test_admin_links_not_displayed_to_logged_out_users(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    add_organization_link = ('a[href="%s"]' %
                             self.uri_for('admin.add_organization'))
    deposit_link = ('a[href="%s"]' % self.uri_for('admin.deposit'))
    history_link = ('a[href="%s"]' % self.uri_for('admin.history'))

    self.assertLength(0, response.pyquery(add_organization_link))
    self.assertLength(0, response.pyquery(deposit_link))
    self.assertLength(0, response.pyquery(history_link))

  def test_logo_has_correct_image_source(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    image = response.pyquery('img[src="/media/logo-small.png"]')
    self.assertLength(1, image)

  def staff_actions_dont_show_for_not_staff(self):
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('components/navbar_private.haml')
    staff_logout_link = ('a[href="%s"]' % self.uri_for('staff.logout'))
    staff_home_link = ('a[href="%s"]' % self.uri_for('staff.home'))
    staff_view_profile_link = ('a[href="%s"]' % self.uri_for('profile.view'))
    staff_deposit_link = ('a[href="%s"]' % self.uri_for('staff.deposit'))
    self.assertLength(0, response.pyquery(staff_deposit_link))
    self.assertLength(0, response.pyquery(staff_logout_link))
    self.assertLength(0, response.pyquery(staff_home_link))
    self.assertLength(0, response.pyquery(staff_view_profile_link))

  @testing.logged_in
  def staff_actions_dont_show_for_not_staff_profile_logged_in(self):
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('components/navbar_private.haml')
    staff_logout_link = ('a[href="%s"]' % self.uri_for('staff.logout'))
    staff_home_link = ('a[href="%s"]' % self.uri_for('staff.home'))
    staff_view_profile_link = ('a[href="%s"]' % self.uri_for('profile.view'))
    staff_deposit_link = ('a[href="%s"]' % self.uri_for('staff.deposit'))
    self.assertLength(0, response.pyquery(staff_deposit_link))
    self.assertLength(0, response.pyquery(staff_logout_link))
    self.assertLength(0, response.pyquery(staff_home_link))
    self.assertLength(0, response.pyquery(staff_view_profile_link))

  @testing.staff_logged_in
  def staff_actions_show_for_staff(self):
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('components/navbar_private.haml')
    staff_logout_link = ('a[href="%s"]' % self.uri_for('staff.logout'))
    staff_home_link = ('a[href="%s"]' % self.uri_for('staff.home'))
    staff_view_profile_link = ('a[href="%s"]' % self.uri_for('profile.view'))
    staff_deposit_link = ('a[href="%s"]' % self.uri_for('staff.deposit'))
    self.assertLength(1, response.pyquery(staff_deposit_link))
    self.assertLength(1, response.pyquery(staff_logout_link))
    self.assertLength(1, response.pyquery(staff_home_link))
    self.assertLength(1, response.pyquery(staff_view_profile_link))

  @testing.staff_logged_in
  @testing.login_as(is_admin=True)
  def staff_actions_show_for_staff_and_profile_logged_in_as_admin(self):
    response = self.app.get(self.uri_for('staff.home'))
    self.assertOk(response)
    self.assertTemplateUsed('components/navbar_private.haml')
    staff_logout_link = ('a[href="%s"]' % self.uri_for('staff.logout'))
    staff_home_link = ('a[href="%s"]' % self.uri_for('staff.home'))
    staff_view_profile_link = ('a[href="%s"]' % self.uri_for('profile.view'))
    add_organization_link = ('a[href="%s"]' %
                             self.uri_for('admin.add_organization'))
    self.assertLength(1, response.pyquery(staff_logout_link))
    self.assertLength(1, response.pyquery(staff_home_link))
    self.assertLength(1, response.pyquery(staff_view_profile_link))
    self.assertLength(1, response.pyquery(add_organization_link))
