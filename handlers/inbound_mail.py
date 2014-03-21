import logging

from google.appengine.api import mail

from handlers import base
from library.auth import login_not_required


class InboundMailHandler(base.BaseHandler):
  @login_not_required
  def update(self, to):
    message = mail.InboundEmailMessage(self.request.body)

    # Ensure that the message always has a subject
    if not hasattr(message, "subject"):
      message.subject = "<no subject>"

    # We want the plaintext version of the body (not the HTML formatted one)
    (_, encoded_body), = list(message.bodies("text/plain"))

    # Split the body into lines and keep all the lines until we see the first
    # "quoted" line (starting with >).
    lines = []

    for line in encoded_body.decode().split("\n"):
      if line.startswith(">"):
        break

      # Strip trailing whitespace and add to the list of lines.
      lines.append(line.rstrip())

    # Get rid of any trailing whitespace from the chunk of text.
    lines = "\n".join(lines).strip().split("\n")

    # If the last line contains noreply@dailymeeting, it's VERY likely a
    # 'reply', so remove it.
    if "noreply@example.com" in lines[-1]:
      lines = lines[:-2]

    # Put the lines back together to form the final body.
    body = "\n".join(lines).strip()

    # Log that the e-mail happened. The record will also exist in the mailbox
    # for update@dailymeetingapp.com.
    template = (u"Received inbound e-mail message:\n"
                u"From: {message.sender}\n"
                u"To: {message.to}\n"
                u"Subject: {message.subject}\n"
                u"Body:\n"
                u"=== Original ===\n"
                u"{original_body}\n"
                u"=== End Original ===\n"
                u"=== Trimmed ===\n"
                u"{body}\n"
                u"=== End Trimmed ===")

    logging.info(template.format(message=message, body=body,
                 original_body=encoded_body.decode()))

    if not body:
      logging.info("Body was empty, skipping note.")
      return

    email = message.sender

    if '<' in email and email.endswith('>'):
      email = email[:-1].split('<', 2)[1]
