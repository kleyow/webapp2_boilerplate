from webapp2_extras import auth
from webapp2_extras import security

from forms import error_messages
from forms.profile_login import ProfileLoginForm
from handlers import base
from library.auth import login_not_required
from models.profile import Profile


class LoginHandler(base.BaseHandler):

  @login_not_required
  def login(self):
    error = False

    if self.request.method == 'POST':
      form = ProfileLoginForm(self.request.POST)

      if form.validate():
        email = form.data['email']
        password = form.data['password']

        user = Profile.get_by_email(email)

        try:
          self.auth.get_user_by_password(email, password)

        except (auth.InvalidAuthIdError, auth.InvalidPasswordError):
          error = error_messages.INVALID_LOGIN

        if user and not user.beta_tester:
          self.session.add_flash(
              value=error_messages.NOT_BETA_TESTER,
              level='error')
          return self.logout()
      else:
        error = True

    if self.get_current_profile():
      redirect = self.request.get('redirect')

      # Prevent an attacker from using Blaze login to redirect to an external
      # website.
      if not redirect.startswith('/'):
        redirect = self.uri_for('home')

      return self.redirect(redirect or self.uri_for('home'))

    return self.render_to_response('login.haml', {'error': error})

  def logout(self):
    self.auth.unset_session()
    self.redirect_to('home')

  @login_not_required
  def forgot_password(self):
    if self.get_current_profile():
      return self.redirect_to('home')

    key = self.request.get('k')
    if key:
      profile = Profile.get_by_activation_key(key)

    else:
      profile = None

    # GET request (either with or without an activation key and profile);
    # We should show either the form to send the recovery e-mail, or the
    # form to change your password.
    if self.request.method == 'GET':
      return self.render_to_response('forgot_password.haml',
                                     {'profile': profile})

    if self.request.method == 'POST':
      email = self.request.POST.get('email', '').strip().lower()
      password = self.request.POST.get('password', '').strip()

      # POST request that had an activation key and a matching profile;
      # We should update their password, log them in, and redirect.
      if key and profile:
        # If we didn't submit a password, then start the process over.
        if not password:
          return self.redirect_to('forgot-password', k=key)

        # Set as activated (since they've confirmed their e-mail).
        profile.activated = True
        profile.put()

        # Change the password for the auth_user.
        user = self.auth.store.user_model.get_by_id(profile.auth_user_id)
        user.password = security.generate_password_hash(password, length=12)
        user.put()

        # Log the user in if beta tester.
        if profile.beta_tester:
          user_id = user.key.id()
          self.auth._user = None
          self.auth.get_user_by_token(user_id, user.create_auth_token(user_id))

       # Redirect to the dashboard.
        return self.redirect_to('home')

      # POST request that didn't find a profile, but POST'ed an e-mail address;
      # We should send them a recovery e-mail.
      elif email and not profile:
        profile = Profile.get_by_email(email)
        if profile:
          profile.activation_key = None
          profile.put()
          context = {'profile': profile}
          self.send_mail(profile=profile, defer=True, context=context,
                         subject='Blaze Password Recovery',
                         template='emails/forgot_password.haml')
        return self.render_to_response('forgot_password.haml')

      # POST request that was missing something...
      # We should redirect back to start the process over.
      else:
        return self.redirect_to('forgot-password')
