from forms import error_messages
from forms.staff import AddStaffForm
from forms.organization import OrganizationEditForm
from handlers import base
from models.organization import Organization
from models.staff import Staff


class OrganizationHandler(base.BaseStaffHandler):

  def view(self, id):
    # Ensure that only staff of an organization can view its page.
    current_staff = self.get_current_staff()
    organization = Organization.get_by_id(int(id))

    if not organization:
      return self.abort(404)

    elif not organization.is_editable_by(current_staff):
      self.session.add_flash(
          value=error_messages.ACCESS_DENIED,
          level='error'
      )
      return self.redirect_to('staff.home')

    else:
      return self.render_to_response('organization_view.haml',
                                     {'organization': organization})

  def edit(self, id):
    organization = Organization.get_by_id(int(id))

    if not organization:
      return self.abort(404)

    elif not organization.is_editable_by(self.get_current_staff()):
      self.session.add_flash(
          value=error_messages.ACCESS_DENIED,
          level='error'
      )
      return self.redirect_to('staff.home')

    else:
      if self.request.method == 'POST':
        form = OrganizationEditForm(self.request.POST)
        if form.validate():
          form.populate_obj(organization)
          organization.put()
          return self.redirect_to('organization.view',
                                  id=organization.key().id())

        else:
          last_error = form.errors.values().pop()
          self.session.add_flash(value=last_error[0], level='error')

      return self.render_to_response('organization_edit.haml',
                                     {'organization': organization})

  def create_staff(self, id):
    if self.request.method == 'POST':
      staff = self.get_current_staff()
      organization = Organization.get_by_id(int(id))

      if not organization.is_editable_by(staff):
        self.session.add_flash(value=error_messages.ACCESS_DENIED,
                               level='error')
        return self.redirect_to('staff.home')

      form = AddStaffForm(self.request.POST)
      if form.validate():
        login = '%s@%s' % (form.data['username'], organization.identifier)

        if Staff.get_by_login(login):
          self.session.add_flash(value=error_messages.STAFF_LOGIN_EXISTS,
                                 level='error')
          return self.render_to_response('organization_view.haml',
                                         {'organization': organization})

        staff = Staff(name=form.data['name'],
                      username=form.data['username'].strip().lower(),
                      parent=organization)

        # Default password for newly made staff is just their login.
        staff.set_password(login)
        staff.put()

        self.session.add_flash(value='Successfully added staff.')
        return self.redirect_to('organization.view',
                                id=organization.key().id())
      else:
        last_error = form.errors.values().pop()
        self.session.add_flash(value=last_error[0], level='error')
        return self.render_to_response('organization_view.haml',
                                       {'organization': organization})

    return self.render_to_response('organization_view.haml',
                                   {'organization': organization})

  def toggle_active(self):
    if self.request.method == 'POST':
      staff = self.get_current_staff()
      login = self.request.POST.get('username', '').strip().lower()
      username, organization_id = login.split('@', 2)
      organization = Organization.get_by_identifier(organization_id)

      if not organization.is_editable_by(staff):
        self.session.add_flash(
            value=error_messages.ACCESS_DENIED,
            level='error'
        )
        return self.redirect_to('staff.home')

      staff = Staff.get_by_login(login)
      staff.is_active = not staff.is_active
      staff.put()

      if staff.is_active:
        self.session.add_flash(value='Successfully enabled staff.')
      else:
        self.session.add_flash(value='Successfully disabled staff.')

      return self.redirect_to('organization.view', id=organization.key().id())
    return self.render_to_response('organization_view.haml',
                                   {'organization': organization})
