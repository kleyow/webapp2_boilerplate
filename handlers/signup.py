from forms import error_messages
from forms.profile import CreateProfileForm
from handlers import base
from library import constants
from library.auth import login_not_required
from models.profile import Profile


class SignupHandler(base.BaseHandler):

  @login_not_required
  def signup(self):
    if self.request.method == 'POST':
      # Create and validate the form.
      form = CreateProfileForm(self.request.POST)
      if form.validate():
        # Create the webapp2_extras.auth user.
        model = self.auth.store.user_model
        ok, user = model.create_user(form.data['email'],
                                     password_raw=form.data['password'])

        if not ok:
          self.session.add_flash(error_messages.EMAIL_IN_USE,
                                 level='error')
          return self.redirect_to('signup')

        # Create the profile.
        profile = Profile(name=form.data['name'], email=form.data['email'],
                          auth_user_id=user.key.id())

        # PIN is hashed in models.profile.Profile.set_pin.
        profile.set_pin(form.data['pin'])
        profile.beta_tester = True
        profile.put()

        # For beta testing do not login the user.

        # Send welcome e-mail.
        self.send_mail(profile=profile, subject='Welcome to Blaze!',
                       template='emails/welcome.haml',
                       context={'profile': profile},
                       reply_to='%s' % (constants.FULL_SUPPORT_EMAIL))

        self.session.add_flash(value='Thanks for registering! '
                                     'Please check your inbox for your '
                                     'activation email.',
                               level='success')

        return self.redirect_to('login')

      else:
        last_error = form.errors.values().pop()
        self.session.add_flash(value=last_error[0], level='error')
        return self.render_to_response('signup.haml', {'form': form})

    return self.render_to_response('signup.haml')

  @login_not_required
  def activate(self):

    key = self.request.get('k')
    profile = Profile.get_by_activation_key(key)

    if key and profile:
      # Set as activated (since they've confirmed their e-mail).
      profile.activated = True
      profile.put()

    # Redirect to the dashboard.
    return self.redirect_to('home')
