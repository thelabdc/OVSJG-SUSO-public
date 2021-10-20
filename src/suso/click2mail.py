"""
This is a simple client for Click2Mail's API. It generally follows the outline
of the Quick Start Guide with Mail Merge::

  https://developers.click2mail.com/rest-api/molpro/getting-started/quick-start-vdp

@author Kevin H. Wilson <kevin.wilson@dc.gov>
"""
import datetime
import os
from posixpath import join as urljoin
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

ADDRESS_CSV_HEADERS = (
    "First_name",
    "Last_name",
    "Organization",
    "Address1",
    "Address2",
    "Address3",
    "City",
    "State",
    "Zip",
    "Country_non-US",
)

PROD_BASE_URL = "https://rest.click2mail.com/molpro"
STAGING_BASE_URL = "https://stage-rest.click2mail.com/molpro"

XML_PARSER = "xml"


def _today():
    """
    Return today's date as a stirng in YYYY-MM-DD format.

    Returns:
      str: Today's date in YYYY-MM-DD format
    """
    return datetime.datetime.now().strftime("%Y-%m-%d")


def _convert_recipient_to_row(recipient):
    """
    Click2Mail expects addresses in a CSV formatted in a particular order.
    This converts a dictionary of the standard described in `post_recipient`
    to the correct order.

    Args:
      recipient (dict[str, str]): A dictionary as described in `post_recipient`
    """
    output = [
        recipient.get(name)
        for name in [
            "firstname",
            "lastname",
            "organization",
            "address",
            "address2",
            "address3",
            "city",
            "state",
            "zipcode",
        ]
    ]

    if recipient.get("country") in ["US", "USA"]:
        output.append(None)
    else:
        output.append(recipient.get("country"))

    return output


def _recipient_row_to_xml(row):
    """
    Convert a recipient (as output by `_convert_recipient_to_row`) into click2mail's
    XML address format.

    Args:
      row (list[str]): The recipient as a list of strings as output
        by `_convert_recipient_to_row`

    Returns:
      str: The converted address
    """
    return (
        "<address>\n  "
        + "\n  ".join(
            "<{key}>{value}</{key}>".format(key=key, value=value or "")
            for key, value in zip(ADDRESS_CSV_HEADERS, row)
        )
        + "\n</address>"
    )


def _recipient_list_to_xml(recipients, address_list_name, address_mapping_id=2):
    """
    Convert a list of recipients (in the format specified by `post_recipients`) into
    a full addressList XML as specified by click2mail.

    Args:
      recipients (list[dict[str, str]]): The recipients to convert into an address list
      address_list_name (str): The name of the address list.
      address_mapping_id (int): The mapping_id of the address list for click2mail. The
        default is 2 and this whole workflow is meant to align with that mapping.

    Returns:
      str: The converted address list
    """
    addresses = "\n".join(
        _recipient_row_to_xml(_convert_recipient_to_row(recipient))
        for recipient in recipients
    )
    return """
    <addressList>
      <addressListName>{name}</addressListName>
      <addressMappingId>{address_mapping_id}</addressMappingId>
      <addresses>
        {addresses}
      </addresses>
    </addressList>""".format(
        addresses=addresses,
        name=address_list_name,
        address_mapping_id=address_mapping_id,
    )


def _get_return_status(response):
    """
    Extract the status and description from a requests.Response object
    returned by click2mail

    Note that a very common catch all status code is 9. You'll need to read
    the description to divine what went wrong.

    Args:
      requests.Response: The response from click2mail

    Returns:
      int: The status code (as documented in their API docs) of the request
      str: the full description of the return
    """
    soup = BeautifulSoup(response.content, XML_PARSER)
    status = int(soup.find("status").text)
    description = soup.find("description").text
    return status, description


def _get_id_from_response(response):
    """
    From an XML document, return the field tagged <id/>

    Args:
      requests.Response: The response from click2mail

    Returns:
      int: The id
    """
    soup = BeautifulSoup(response.content, XML_PARSER)
    return int(soup.find("id").text)


def _raise_errors(response, extra_text="", allowed_status=()):
    """
    Custom functions to raise errors if a 2xx is not returned requests.

    Args:
      response (requests.Response): the response from the request
      extra_text (str): Some text to add to the error message indicating where
        the error came from

    Raises:
      ValueError: If anything went wrong
    """
    if not response.ok:
        raise ValueError(
            "Something went wrong {}: {}".format(extra_text, response.content)
        )
    status, description = _get_return_status(response)
    if not status:
        return
    if status not in allowed_status:
        raise ValueError("Something went wrong: {} {}".format(extra_text, description))


class ReturnAddress:
    """
    An object representing a return address
    """

    def __init__(
        self,
        name=None,
        organization=None,
        address=None,
        city=None,
        state=None,
        zipcode=None,
    ):
        self.name = name
        self.organization = organization
        self.address = address
        self.city = city
        self.state = state
        self.zipcode = zipcode

    def to_json(self):
        """
        Convert to a dictionary whose keys are in compliance with click2mail's
        requirements for determining the return address in a job.

        Returns:
          dict[str, str]: Form data for click2mail's return address
        """
        return {
            "rtnName": self.name,
            "rtnOrganization": self.organization,
            "rtnAddress1": self.address,
            "rtnCity": self.city,
            "rtnState": self.state,
            "rtnZip": self.zipcode,
        }


class Click2MailClient:
    """
    Interact with Click2Mail via their API. The general flow, after creating this class,
    is to:
      * login
      * create_job
      * post_recipients
      * (TODO) poll_recipients
      * update_job
      * submit_job
    """

    def __init__(self, is_production=False):
        """
        Create the client indicating whether or not this is production.

        Args:
          is_production (bool): Is this production?
        """
        self._client = None
        self._username = None
        self._password = None
        self._session = None

        self.return_address = ReturnAddress()

        self.is_production = is_production
        self._base_url = PROD_BASE_URL if is_production else STAGING_BASE_URL

    def login(self, username, secret_key):
        """
        Log in. Your username is your usual username from Click2Mail. You must
        setup a secret key from their interface.

        Args:
          username (str): Your username
          secret_key (str): The secret key that you procure from the web interface
        """
        self._username = username
        self._secret_key = secret_key
        self._auth = HTTPBasicAuth(username, secret_key)

    @property
    def base_url(self):
        """
        The base url of the API. All other calls are relative to this url.
        """
        return self._base_url

    @property
    def auth(self):
        return self._auth

    @property
    def session(self):
        if not self._session:
            self._session = requests.session()
        return self._session

    def _post(self, *args, query=None, **kwargs):
        """
        POST a request to join(self.base_url, *args) with the given kwargs.
        This will automatically include auth information.

        Args:
          args (list): Arguments to be joined to self.base_url to form a request
          query (dict): A dictionary of query args to pass to the API
          kwargs (dict): kwargs to be passed to requests for the request

        Returns:
          requests.Response: The response from the POST.
        """
        url = urljoin(self.base_url, *map(str, args))
        if query:
            url += "?" + urlencode(query)
        return self.session.post(url, auth=self.auth, **kwargs)

    def _get(self, *args, query=None, **kwargs):
        """
        GET a request to join(self.base_url, *args) with the given kwargs.
        This will automatically include auth information.

        Args:
          args (list): Arguments to be joined to self.base_url to form a request
          query (dict): A dictionary of query args to pass to the API
          kwargs (dict): kwargs to be passed to requests for the request

        Returns:
          requests.Response: The response from the GET.
        """
        url = urljoin(self.base_url, *map(str, args))
        if query:
            url += "?" + urlencode(query)
        return self.session.get(url, auth=self.auth, **kwargs)

    def post_document(
        self,
        document_pdf,
        document_name=None,
        document_class="Letter 8.5 x 11",
        document_format="PDF",
    ):
        if not document_name:
            name = os.path.basename(document_pdf.rsplit(".", 1)[0])
            document_name = "SUSO {date} {name}".format(date=_today(), name=name)

        data = {
            "documentName": document_name,
            "documentClass": document_class,
            "documentFormat": document_format,
        }
        pdf_name = os.path.basename(document_pdf)
        with open(document_pdf, "rb") as f:
            response = self._post("documents", data=data, files={"file": f})
        _raise_errors(response, "uploading the document")

        soup = BeautifulSoup(response.content, XML_PARSER)
        document_id = int(soup.find("id").text)
        return document_id

    def create_job_from_template(self, template_name):
        """
        Create a new job from a template name.

        Args:
          template_name (str): The name of the template

        Returns:
          (int): The id of the created job
        """
        response = self._post(
            "jobs", "jobTemplate", query={"templateName": template_name}
        )
        _raise_errors(response, "creating the job")

        soup = BeautifulSoup(response.content, XML_PARSER)
        job_id = int(soup.find("id").text)
        return job_id

    def set_return_address(self, name, organization, address, city, state, zipcode):
        """
        Set the return address to use for all the jobs created with this client.

        Args:
          name (str): The name field of the address
          organization (str): The organization field of the address
          address (str): The address field of the address
          city (str): The city field of the address
          state (str): The state field of the address
          zipcode (str): The zipcode field of the address
        """
        self.return_address.name = name
        self.return_address.organization = organization
        self.return_address.address = address
        self.return_address.city = city
        self.return_address.state = state
        self.return_address.zipcode = zipcode

    def create_job(
        self, document_id, address_list_id, document_class="Letter 8.5 x 11"
    ):
        data = {
            "documentClass": document_class,
            "layout": "Picture and Address First Page",
            "productionTime": "Next Day",
            "envelope": "#10 Open Window Envelope",
            "color": "Full Color",
            "paperType": "White 24#",
            "printOption": "Printing One side",
            "documentId": document_id,
            "addressId": address_list_id,
        }
        data.update(self.return_address.to_json())
        r = self._post("jobs", data=data)
        _raise_errors(r, "creating job")

        return _get_id_from_response(r)

    def post_recipients(self, recipients, address_list_name):
        """
        Create an address list of recipients of the job. Recipients are a list of
        dictionaries with the keys:
          * firstname
          * lastname
          * organization
          * address
          * address2
          * address3
          * city
          * state
          * zipcode
          * country

        Args:
          recipients (list[dict[str, str]]): The list of recipients in the format indicated.
          address_list_name (str): The display name of the address list to be created.

        Returns:
          int: The id of the address list
        """
        address_list = _recipient_list_to_xml(recipients, address_list_name)
        headers = requests.utils.default_headers()
        headers["Content-Type"] = "application/xml"

        # TODO (kevin): Apparently need to poll to understand if there are address errors
        # See https://developers.click2mail.com/rest-api/molpro/docs/reference#addressLists
        # for more info
        response = self._post("addressLists", headers=headers, data=address_list)
        _raise_errors(response, extra_text="posting addresses", allowed_status=(3,))
        return _get_id_from_response(response)

    def update_job(self, job_id, address_list_id):
        """
        Set the address list of the job you created.

        Args:
          job_id (int): The id of the job to update
          address_list_id (int): The address list for the job
        """
        url = urljoin(self.base_url, "jobs", job_id, "update")
        data = urlencode({"addressId": address_list_id})
        response = requests.post(url, data=data, auth=self.auth)
        _raise_errors(response, "updating job")

    def submit_job(self, job_id, billing_type="Invoice"):
        """
        Submit the job. Note that when you submit this, you will be charged.

        Args:
          job_id (int): The job to submit
          billing_type (str): How to bill the job. Possible values are 'User Credit' or 'Invoice'
        """
        return self._post(
            "jobs", str(job_id), "submit", data={"billingType": billing_type}
        )

    def get_tracking_data(self, job_id):
        response = self._get(
            "jobs", str(job_id), "tracking", query={"trackingType", "IMB"}
        )
        soup = BeautifulSoup(response.content, XML_PARSER)
        try:
            piece = soup.find("tracking").find("mailPiece")
            status = piece.find("status").text
            status_time = piece.find("dateTime").text
        except AttributeError:
            return None, None
        return status, status_time
