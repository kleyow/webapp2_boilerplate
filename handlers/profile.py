from webapp2_extras import security

from forms import error_messages
from forms.profile import UpdateProfileForm
from handlers import base
from library import constants
from models.profile import Profile


class ProfileHandler(base.BaseHandler):

  def view(self):
    return self.render_to_response('profile_view.haml')

  def update(self):
    if self.request.method == 'POST':
      profile = self.get_current_profile()
      form = UpdateProfileForm(self.request.POST, obj=profile)
      user = self.auth.store.user_model.get_by_id(profile.auth_user_id)

      # Validate the form.
      if form.validate():
        # Grabs email for verification and PIN.
        email = form.data['email']
        old_password = form.data['old_password']
        pin = form.data['pin']
        new_password = form.data['new_password']

        # If the user attempts to change their password, email address or pin.
        # they should be required to confirm their password.
        if new_password or pin:
          if not old_password:
            error = error_messages.PASSWORD_REQUIRED_UPDATE

          elif not security.check_password_hash(old_password, user.password):
            error = error_messages.PASSWORD_INVALID

          # Ensures the email is not in use.
          elif email != profile.email and Profile.get_by_email(email):
            error = error_messages.EMAIL_INVALID_OR_USED

          else:
            error = None

          if error:
            self.session.add_flash(value=error, level='error')
            return self.render_to_response('update_profile.haml')

        # Get the current profile and updates information.
        profile.name = form.data['name']

        # If an email was submitted, update the profile email and the
        # auth_ids property of webapp2_extras.appengine.auth.models.User
        # associated with the Profile.
        if email and email != profile.email:
          user.auth_ids.remove(profile.email)
          profile.email = email
          user.auth_ids.append(profile.email)

          # Deactivate the profile, change their activation code, and resend
          # an activation email.
          profile.activated = False
          profile.activation_key = None

          # Ensure changes to the profile are saved, so the profile has an
          # activation key in the email.
          profile.put()

          self.send_mail(profile=profile, subject='Welcome to Blaze!',
                         template='emails/welcome.haml',
                         context={'profile': profile},
                         reply_to='%s' % (constants.FULL_SUPPORT_EMAIL))

        # If PIN is provided, update it.
        if pin:
          profile.set_pin(pin)

        profile.put()

        # Updates user password if a new one is provided.
        if new_password:
          user.password = security.generate_password_hash(new_password,
                                                          length=12)
        # Reload the profile and user so changes show immediately
        # throughout the system.
        user.put().get()
        Profile.get(profile.key())
        return self.redirect_to('home')

      else:
        last_error = form.errors.values().pop()
        self.session.add_flash(last_error[0], level='error')

    return self.render_to_response('update_profile.haml')
