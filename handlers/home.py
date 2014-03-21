from handlers import base
from library.auth import login_not_required
from models.transaction import Transaction


class HomeHandler(base.BaseHandler):

  @login_not_required
  def home(self):
    if self.get_current_profile():
      return self.private_home()
    else:
      return self.public_home()

  @login_not_required
  def public_home(self):
    # Switch this to home.haml when we're ready to launch publicly.
    template_file = 'landing.haml'
    return self.render_to_response(template_file, use_cache=True)

  def private_home(self):
    return self.render_to_response('home.haml',
                                   {'Transaction': Transaction})
