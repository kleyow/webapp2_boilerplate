from webapp2_extras import jinja2


class SilentUndefined(jinja2.jinja2.Undefined):
  __unicode__ = lambda *args, **kwargs: u''
  __str__ = __unicode__

  __bool__ = lambda *args, **kwargs: False

  __call__ = lambda self, *args, **kwargs: self.__class__()
  __getattr__ = __call__
