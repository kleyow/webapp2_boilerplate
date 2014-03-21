import unittest2

from forms import error_messages
from library import testing
from models.organization import Organization
from models.staff import Staff


class TestOrganizationEdit(testing.TestCase, unittest2.TestCase):

  def test_get_organization_edit_page_not_logged_in(self):
    organization = self.create_organization()
    edit_url = self.uri_for('organization.edit', id=organization.key().id())
    response = self.app.get(edit_url)
    self.assertRedirects(
        response, self.uri_for('staff.login', redirect=edit_url))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_get_organization_edit_page_logged_in_admin(self):
    organization = self.get_current_staff().get_organization()
    response = self.app.get(self.uri_for('organization.edit',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_edit.haml')
    edit_url = self.uri_for('organization.edit', id=organization.key().id())
    edit_form = response.pyquery('#organization-edit form#edit-form')
    self.assertEqual(edit_url, edit_form.attr('action'))

  @testing.login_as_staff(role=Staff.Role.Manager)
  def test_get_organization_edit_page_logged_in_manager(self):
    organization = self.get_current_staff().get_organization()
    response = self.app.get(self.uri_for('organization.edit',
                                         id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('organization_edit.haml')
    edit_url = self.uri_for('organization.edit', id=organization.key().id())
    edit_form = response.pyquery('#organization-edit form#edit-form')
    self.assertEqual(edit_url, edit_form.attr('action'))

  @testing.staff_logged_in
  def test_get_organization_edit_page_logged_in_staff(self):
    organization = self.get_current_staff().get_organization()
    response = self.app.get(self.uri_for('organization.edit',
                                         id=organization.key().id()))
    self.assertRedirects(response, self.uri_for('staff.home'))
    self.assertFlashMessage(
        level='error', message=error_messages.ACCESS_DENIED)

  def test_post_organization_edit_page_not_logged_in_as_staff(self):
    organization = self.create_organization()
    edit_url = self.uri_for('organization.edit', id=organization.key().id())
    response = self.app.post(edit_url)
    self.assertRedirects(
        response, self.uri_for('staff.login', redirect=edit_url))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_submit_organization_edit_form_logged_in_as_staff(self):
    organization = self.get_current_staff().get_organization()
    params = {'name': 'NEW NAME', 'email': 'email@example.com'}
    response = self.app.get(self.uri_for('organization.edit',
                                         id=organization.key().id()), params)
    form = response.forms['edit-form']
    form['name'] = params['name']
    response = form.submit()
    self.assertRedirects(response, self.uri_for('organization.view',
                                                id=organization.key().id()))
    organization = Organization.get(organization.key())
    self.assertEqual(params['name'], organization.name)

    # Ensure that the edit method doesn't create a new entity.
    self.assertLength(1, Organization.all())

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_only_owner_can_post_organization_edit_page(self):
    staff_staff = self.create_staff('test@example.com')
    organization = self.create_organization(staff=[staff_staff.key()])

    response = self.app.post(self.uri_for('organization.edit',
                                          id=organization.key().id()))
    self.assertRedirects(response, self.uri_for('staff.home'))

    # Attempt access as the staff member.
    self.logout()
    self.login('test@example.com')
    response = self.app.post(self.uri_for('organization.edit',
                                          id=organization.key().id()))
    self.assertRedirects(response, self.uri_for('staff.home'))

  @testing.login_as_staff(role=Staff.Role.Admin)
  def test_empty_form_submission_displays_error(self):
    organization = self.get_current_staff().get_organization()

    params = {'email': '', 'name': ''}

    response = self.app.post(self.uri_for('organization.edit',
                                          id=organization.key().id()), params)
    self.assertFlashMessage(message=error_messages.ORG_NAME_REQUIRED,
                            level='error', response=response)
