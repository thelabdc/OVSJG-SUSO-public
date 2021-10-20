import textwrap

from bs4 import BeautifulSoup

from suso import click2mail

JOHN_DOE = {
    "firstname": "John",
    "lastname": "Doe",
    "address": "1350 Pennsylvania Avenue",
    "city": "Washington",
    "state": "DC",
    "zipcode": "20004",
    "country": "USA",
}

JANE_ROE = {
    "firstname": "Jane",
    "lastname": "Roe",
    "address": "441 4th Street",
    "city": "Washington",
    "state": "DC",
    "zipcode": "20003",
    "country": "USA",
}


def _check_dict(soup, d):
    assert soup.find("First_name").text == d.get("firstname", "")
    assert soup.find("Last_name").text == d.get("lastname", "")
    assert soup.find("Organization").text == d.get("organization", "")
    assert soup.find("Address1").text == d.get("address", "")
    assert soup.find("Address2").text == d.get("address2", "")
    assert soup.find("Address3").text == d.get("address3", "")
    assert soup.find("City").text == d.get("city", "")
    assert soup.find("State").text == d.get("state", "")
    assert soup.find("Zip").text == d.get("zipcode", "")
    assert soup.find("Country_non-US").text == ""


def test__convert_recipient_to_row():
    converted = click2mail._convert_recipient_to_row(JOHN_DOE)
    assert converted == [
        "John",
        "Doe",
        None,
        "1350 Pennsylvania Avenue",
        None,
        None,
        "Washington",
        "DC",
        "20004",
        None,
    ]


def test__recipient_row_to_xml():
    converted = click2mail._recipient_row_to_xml(
        click2mail._convert_recipient_to_row(JOHN_DOE)
    )
    _check_dict(BeautifulSoup(converted, click2mail.XML_PARSER), JOHN_DOE)


class MockResponse:
    def __init__(self, content):
        self.content = content


def test__get_return_status():
    example_return = textwrap.dedent(
        """\
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <job>
      <id>245985</id>
      <status>0</status>
      <description>Created</description>
      <statusUrl>https://rest.click2mail.com/molpro/jobs/245985</statusUrl>
    </job>
    """
    )

    mock_response = MockResponse(example_return)
    status, description = click2mail._get_return_status(mock_response)
    assert status == 0
    assert description == "Created"


def test__recipient_list_to_xml():
    output = click2mail._recipient_list_to_xml([JOHN_DOE, JANE_ROE], "aList")
    soup = BeautifulSoup(output, click2mail.XML_PARSER)

    address_lists = soup.findAll("addressList")
    assert len(address_lists) == 1
    address_list = address_lists[0]

    assert address_list.find("addressListName").text == "aList"
    assert int(address_list.find("addressMappingId").text) == 2

    addresses = address_list.findAll("address")
    assert len(addresses) == 2

    for address in addresses:
        to_compare = JOHN_DOE if address.find("First_name").text == "John" else JANE_ROE
        _check_dict(address, to_compare)
