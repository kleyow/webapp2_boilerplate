import webapp2

from config import webapp2_config
from handlers import errors
from routes import application_routes


app = webapp2.WSGIApplication(routes=application_routes,
                              config=webapp2_config)

app.error_handlers[404] = errors.Webapp2HandlerAdapter(errors.Handle404)
app.error_handlers[500] = errors.Webapp2HandlerAdapter(errors.Handle500)
