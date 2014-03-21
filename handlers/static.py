from handlers.base import BaseHandler
from library import auth


def StaticHandler(template, login_required=True, use_cache=True):
  """Generates a handler that can render the specified template."""

  if login_required:
    decorator = auth.login_required
  else:
    decorator = auth.login_not_required

  class Handler(BaseHandler):

    @decorator
    def get(self):
      return self.render_to_response(template, use_cache=use_cache)

  return Handler


def PublicStaticHandler(template, use_cache=True):
  """Static handler where no login is required."""

  return StaticHandler(template, login_required=False, use_cache=use_cache)
