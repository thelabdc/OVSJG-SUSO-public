"""
The hard work of reifying the MailChimp API into a Python library has been
done by someone else::

  https://github.com/charlesthk/python-mailchimp

However, we expose some specific features that we need here from that API.
The raw client can be found by calling `obj.client`.

@author Kevin H. Wilson <kevin.wilson@dc.gov>
"""
import requests
from mailchimp3 import MailChimp

from .constants import DEFAULT_USER_AGENT


class MailChimpClient:
  def __init__(self):
    self._client = None

  @property
  def client(self):
    if not self._client:
      raise ValueError("You must `login` before you can use the client")
    return self._client

  def login(self, username, secret_key, timeout=10.0, user_agent=DEFAULT_USER_AGENT):
    """
    Log in. Your username is your usual username from MailChimp. You must
    setup a secret key from their interface.

    Args:
      username (str): Your username
      secret_key (str): The secret key that you procure from the web interface
      timeout (float): The time (in seconds) before killilng a hanging request
      user_agent (str): The User-Agent to call the API with (used by MailChimp to record
        where a request is from)
    """
    headers = requests.utils.default_headers()
    headers['User-Agent'] = user_agent
    self._client = MailChimp(username, secret_key, timeout=timeout, request_headers=headers)

  def post_recipient(self, list_id, email, firstname, lastname):
    """
    Post a recipient to the given list.

    TODO (kevin): This should probably be batched::

      https://developer.mailchimp.com/documentation/mailchimp/reference/batches/

    Args:
      list_id (str): The id of the list to subscribe the user to
      email (str): The email of the user
      firstname (str): The user's first name
      lastname (str): The user's last name

    Returns:
      dict: The possible calls you could make about this user
    """
    return self.client.lists.members.create(list_id, {
      'email_address': email,
      'status': 'subscribed',
      'merge_fields': {
        'FNAME': firstname,
        'LNAME': lastname,
      }
    })
