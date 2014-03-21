import wtforms


class ProfileLoginForm(wtforms.Form):

  email = wtforms.TextField()
  password = wtforms.TextField()

  def validate_email(self, field):
    field.data = field.data.strip().lower()

  def validate_password(self, field):
    field.data = field.data.strip()
