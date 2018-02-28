import mailchimp3


DEFAULT_LIST_ID = None


def get_client(username, key):
  """
  Get a mailchimp client object. See the mailchimp3 documentation for how to use it.

  Arguments:
    username (str): The username associated with the key passed
    key (str): The API key to use with the mailchimp client

  Returns:
    mailchimp3.MailChimp: The client
  """
  return mailchimp3.MailChimp(mc_user=username, mc_api=key)


def send_email(client, name, text, subject=None, from_name='Kevin Wilson Bot',
               reply_to='kevin.wilson@dc.gov', list_id=DEFAULT_LIST_ID):
  """
  Send an email with the passed client.

  Arguments:
    client (mailchimp3.MailChimp): The client
    name (str): The name to use for the mailchimp template. Also the default subject
      line if subject is None.
    text (str): The text of the email to send
    subject (str | None): The subject of the email to send. If None, is `name`
    from_name (str): The display name of the person from whom the email will be from
    reply_to (str): The email address that replies to the email will be sent to
    list_id (str): The id of the mailing list to send the email to (this is maintained
      on mailchimp's website)

  Returns:
    dict[str, str]: Information about the sent email
  """
  subject = subject or name
  t = client.templates.create({'name': name, 'html': text})
  template_id = t['id']

  c = client.campaigns.create({
    'recipients': {
      'list_id': list_id
    },
    'settings': {
      'subject_line': name,
      'from_name': from_name,
      'reply_to': reply_to,
      'template_id': template_id
    },
    'type': 'plaintext'}
  )
  campaign_id = c['id']

  return client.campaigns.actions.send(campaign_id)
