import pytz
import wtforms
from wtforms import validators, ValidationError

from forms import error_messages
from models.profile import Profile


class AbstractProfileForm(wtforms.Form):

  name = wtforms.TextField(
      validators=[
          validators.Required(error_messages.NAME_REQUIRED),
          validators.Length(message=error_messages.NAME_TOO_LONG, max=500)])


class UpdateProfileForm(AbstractProfileForm):

  email = wtforms.TextField(
      validators=[validators.Optional(),
                  validators.Email(error_messages.INVALID_EMAIL)])

  old_password = wtforms.PasswordField(validators=[validators.Optional()])

  new_password = wtforms.PasswordField(validators=[validators.Optional()])

  pin = wtforms.TextField(
      validators=[validators.Optional(),
                  validators.Regexp('\d{4}',
                                    message=error_messages.PIN_INVALID)])


class CreateProfileForm(AbstractProfileForm):

  email = wtforms.TextField(
      validators=[validators.Required(error_messages.EMAIL_REQUIRED),
                  validators.Email(error_messages.INVALID_EMAIL)])

  password = wtforms.PasswordField(
      validators=[validators.Required(error_messages.PASSWORD_REQUIRED)])

  pin = wtforms.TextField(
      validators=[validators.Required(error_messages.PIN_INVALID),
                  validators.Regexp('\d{4}',
                                    message=error_messages.PIN_INVALID)])

  timezone = wtforms.TextField(validators=[
      validators.Optional(),
      validators.AnyOf(pytz.common_timezones)],
      default='UTC')

  def validate_email(self, field):
    if Profile.get_by_email(field.data):
      raise ValidationError(error_messages.EMAIL_INVALID_OR_USED)

    field.data = field.data.lower()
