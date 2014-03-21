import wtforms
from wtforms import validators


class StaffLoginForm(wtforms.Form):

  username = wtforms.TextField(
      validators=[validators.Regexp('[a-zA-Z0-9]+@[a-zA-Z0-9]+')])
  password = wtforms.TextField()

  def validate_username(self, field):
    field.data = field.data.strip().lower()

  def validate_password(self, field):
    field.data = field.data.strip()
