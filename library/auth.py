def login_not_required(handler_method):
  """Allows someone to *not* be logged in.

  The login_required attribute is inspected by handlers.base.BaseHandlerMeta
  and is used as the flag for whether to wrap a method with login_required
  or not.
  """
  handler_method.login_required = False
  return handler_method


def login_required(handler_method):
  """Requires that this person be logged in."""

  already_wrapped = getattr(handler_method, 'wrapped', False)
  login_required = getattr(handler_method, 'login_required', True)

  # If the method doesn't require a login, or has already been wrapped,
  # just return the original.
  if not login_required or already_wrapped:
    return handler_method

  # This method wraps handlers that require logged-in users.
  def wrapped_handler(self, *args, **kwargs):
    if user_is_logged_in(self):
      return handler_method(self, *args, **kwargs)
    else:
      uri = self.uri_for('login', redirect=self.request.path)
      self.redirect(uri, abort=True)

  # Let others know that this method is already wrapped to avoid wrapping
  # it more than once.
  wrapped_handler.wrapped = True

  return wrapped_handler


def staff_required(handler_method):
  """Requires that the user be a staff member."""

  already_wrapped = getattr(handler_method, 'staff_wrapped', False)
  login_required = getattr(handler_method, 'login_required', True)

  if not login_required or already_wrapped:
    return handler_method

  # This method wraps handlers that require logged-in staff users.
  def wrapped_handler(self, *args, **kwargs):
    if self.get_current_staff():
      return handler_method(self, *args, **kwargs)

    # They are not staff; redirect them to the staff login.
    else:
      uri = self.uri_for('staff.login', redirect=self.request.path)
      return self.redirect(uri, abort=True)

  # Prevent this handler from being wrapped multiple times.
  wrapped_handler.staff_wrapped = True

  return wrapped_handler


def admin_required(handler_method):
  """Requires that the user be an Administrator."""

  already_wrapped = getattr(handler_method, 'admin_wrapped', False)

  if already_wrapped:
    return handler_method

  # This method wraps handlers that require logged-in administrator users.
  def wrapped_handler(self, *args, **kwargs):
    # If the user is logged in, and is an administrator, grant them access.
    if user_is_logged_in(self):
      # The user is logged in; check if they're an admin.
      if self.get_current_profile().is_admin:
        return handler_method(self, *args, **kwargs)

      # They are not an admin; redirect them elsewhere.
      else:
        self.session.add_flash('You are not authorized to view this page.',
                               level='error')
        return self.redirect_to('home')

    # If the user isn't logged in, redirect them to the login.
    else:
      uri = self.uri_for('login', redirect=self.request.path)
      return self.redirect(uri, abort=True)

  # Prevent this handler from being wrapped multiple times.
  wrapped_handler.admin_wrapped = True

  return wrapped_handler


def user_is_logged_in(handler):
  """Ensures a user is logged in.
  This method checks if a user is attached to the handler's current session,
  and that the handler's current profile exists."""
  return handler.auth.get_user_by_session() and handler.get_current_profile()
