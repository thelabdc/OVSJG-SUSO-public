import re
from datetime import datetime
from posixpath import join as urljoin
from urllib.parse import urlencode

import pandas as pd
import requests
from pandas.io.json import json_normalize

BASE_URL = "https://services.etosoftware.com/API"


def _list_to_dict(l, key_key, value_key):
    """
    Convert a list of dictionaries with at least keys key_key and value_key
    into a dictionary whose keys are key_key's value and whose values are
    value_key's value.

    Args:
      l (list[dict]): The list to convert to a dictionary
      key_key: the key for the key of the returned dictionary
      value_key: the key for the value of the returned dictionary

    Returns:
      dict: The converted dictionary
    """
    return {elt[key_key]: elt[value_key] for elt in l}


def convert_date(d):
    g = re.search(r"^/Date\((\d+)-\d+\)/$", d.strip())
    if g:
        return datetime.fromtimestamp(int(g.groups()[0]) / 1000).strftime("%Y-%m-%d")
    return None


class ApiHandler:
    """
    A class for handling interactions with ETO's API
    """

    def __init__(self, base_url=BASE_URL, session=None, timezone_offset=0):
        self.base_url = base_url
        self._session = session
        self.timezone_offset = timezone_offset

        self._auth_token = None
        self._enterprise_id = None
        self._security_token = None

        self._sites = None
        self._site_id = None
        self._program_id = None

    @property
    def session(self):
        """The HTTP session the class maintains"""
        if not self._session:
            self._session = requests.session()
        return self._session

    @property
    def auth_token(self):
        """The auth token; set after running `login`"""
        if not self._auth_token:
            raise ValueError("You can't call auth_token before calling login")
        return self._auth_token

    @property
    def enterprise_id(self):
        """The enterprise id; set after running `login`"""
        if not self._enterprise_id:
            raise ValueError("You can't call enterprise_id before calling login")
        return self._enterprise_id

    @property
    def security_token(self):
        """The security token; set after calling `login_site`"""
        if not self._security_token:
            raise ValueError("You can't call security_token before calling login_site")
        return self._security_token

    @property
    def site_id(self):
        if not self._site_id:
            raise ValueError("You can't call site_id before calling `login_site`")
        return self._site_id

    @property
    def site_name(self):
        if not self._site_id:
            raise ValueError("You can't call site_name before calling `login_site`")
        return self._sites[self._site_id]

    @property
    def program_id(self):
        if not self._program_id:
            raise ValueError("You can't call program_id before calling `login_site`")
        return self._program_id

    def _request(self, method, *args, query=None, **kwargs):
        """
        Make an HTTP request with the given method and query parameters to
        self.base_url + urljoin(*args). **kwargs are passed as-is to the requests session.

        Args:
          method (str): The HTTP method
          *args: The components of the URL's path
          query (dict): The query arguments to be URL encoded
          kwargs: Remaining kwargs to pass to requests.request

        Returns:
          requests.Response: The requests Response object
        """
        url = urljoin(self.base_url, *map(str, args))
        if query:
            url += "?" + urlencode(query)
        return self.session.request(method, url, **kwargs)

    def _request_site(self, method, *args, query=None, **kwargs):
        """
        Make an HTTP request with the given method and query parameters to
        self.base_url + urljoin(*args). **kwargs are passed as-is to the requests session.

        Uses the security information obtained from `login` and `login_site`

        Args:
          method (str): The HTTP method
          *args: The components of the URL's path
          query (dict): The query arguments to be URL encoded
          kwargs: Remaining kwargs to pass to requests.request

        Returns:
          requests.Response: The requests Response object
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "enterpriseGuid": self.enterprise_id,
            "securityToken": self.security_token,
        }
        return self._request(method, *args, query=query, headers=headers, **kwargs)

    def _get(self, *args, query=None, **kwargs):
        return self._request("get", *args, query=query, **kwargs)

    def _get_site(self, *args, query=None, **kwargs):
        return self._request_site("get", *args, query=query, **kwargs)

    def _post(self, *args, query=None, **kwargs):
        return self._request("post", *args, query=query, **kwargs)

    def _post_site(self, *args, query=None, **kwargs):
        return self._request_site("post", *args, query=query, **kwargs)

    def login(self, username, password):
        payload = {"security": {"Email": username, "Password": password}}
        auth = self._post("Security.svc", "SSOAuthenticate/", json=payload).json()
        self._auth_token = auth["SSOAuthenticateResult"]["SSOAuthToken"]

        r = self._get("Security.svc", "GetSSOEnterprises/", self.auth_token)
        self._enterprise_id = r.json()[0]["Key"]

    def get_sites(self, filter_historical=True):
        if self._sites:
            return self._sites

        r = self._get(
            "Security.svc", "GetSSOSites/", self.auth_token, self.enterprise_id
        )
        self._sites = _list_to_dict(r.json(), "Key", "Value")
        if filter_historical:
            self._sites = {
                k: v for k, v in self._sites.items() if not v.startswith("Historical")
            }
        return self._sites

    def login_site(self, site_id):
        r = self._get(
            "Security.svc",
            "SSOSiteLogin/",
            site_id,
            self.enterprise_id,
            self.auth_token,
            self.timezone_offset,
        )
        self._security_token = r.json()
        self._site_id = site_id

        r = self._get_site("Form.svc", "Forms", "Program", "GetPrograms", self.site_id)
        data = _list_to_dict(r.json(), "Name", "ID")
        program_id = data.get("SUSO")
        if not program_id:
            raise ValueError(
                f"Site {self.site_id} (self.site_name) has no SUSO program"
            )

        r = self._post_site(
            "Security.svc", "UpdateCurrentProgram/", json={"ProgramID": str(program_id)}
        )
        self._program_id = program_id
        return r.json()

    def get_participants(self, start_date, end_date):
        query = {
            "program": self.program_id,
            "startdate": start_date,
            "enddate": end_date,
            "flag": "enrolled",
        }
        r = self._get_site("Search.svc", "Search", "Enrollment", query=query)
        output = r.json()
        if not output:
            return pd.DataFrame()
        for datum in output:
            datum.update(
                {
                    "site_id": self.site_id,
                    "site_name": self.site_name,
                    "program_name": "SUSO",
                    "program_id": self.program_id,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        output = json_normalize(output)

        # Append demographic data
        demo_data = []
        for clid in output.CLID.unique():
            r = self._get_site(
                "Actor.svc", "participant", clid, query={"MaskSSN": "True"}
            )
            j = r.json()
            data = j["CustomDemoData"] if j else {}
            data = _list_to_dict(data, "CDID", "value")
            demo_data.append(
                {
                    "CLID": clid,
                    "guardian_firstname": data.get(3771),
                    "guardian_lastname": data.get(3774),
                    "SubjectID": j.get("SubjectID"),
                    "address": j.get("Address1"),
                    "zipcode": j.get("ZipCode"),
                }
            )

        demo_df = pd.DataFrame.from_records(
            [],
            columns=[
                "CLID",
                "guardian_firstname",
                "guardian_lastname",
                "SubjectID",
                "address",
                "zipcode",
            ],
        )
        demo_df = pd.concat([demo_df, json_normalize(demo_data)])
        output = output.merge(demo_df, how="left", on="CLID")

        # Append touchpoint data
        subject_data = []
        for subject_id in output.SubjectID.dropna().astype(int).unique():
            r = self._get_site(
                "TouchPoint.svc",
                "ListTouchPointResponses",
                query={"SubjectID": str(subject_id), "TouchpointID": "68"},
            )
            j = r.json() or []
            for elt in j:
                data = elt["ResponseElements"]
                data = _list_to_dict(data, "ElementID", "Value")
                subject_datum = {
                    "SubjectID": subject_id,
                    "AuditStaffID": r.json()[0]["AuditStaffID"] if r.json() else None,
                    "referral_date": data.get(1001),
                    "referral_source": data.get(1002),
                    "grade": data.get(1006),
                    "unexcused_absences": data.get(1007),
                    "is_high_risk": data.get(1012),
                    "school_name": data.get(1187),
                    "current_referral_status": data.get(1194),
                    "youth_club1": data.get(1207),
                    "youth_club2": data.get(1211),
                }
                subject_data.append(subject_datum)
        # In case subject_data is empty, make sure we at least have the column names
        subject_df = pd.DataFrame.from_records(
            [],
            columns=[
                "SubjectID",
                "AuditStaffID",
                "referral_date",
                "referral_source",
                "grade",
                "unexcused_absences",
                "is_high_risk",
                "school_name",
                "current_referral_status",
                "youth_club1",
                "youth_club2",
            ],
        )
        subject_df = pd.concat([subject_df, json_normalize(subject_data)])

        # Merge data back in
        output = output.merge(subject_df, how="left", on="SubjectID")

        # Append staff data
        staff_data = []
        for staff_id in output.AuditStaffID.dropna().astype(int).unique():
            r = self._get_site("Staff.svc", staff_id)
            data = r.json()
            staff_data.append(
                {
                    "AuditStaffID": staff_id,
                    "staff_last_name": data["LastName"],
                    "staff_first_name": data["FirstName"],
                    "staff_email": data["Email"],
                }
            )
        staff_df = pd.DataFrame.from_records(
            [],
            columns=[
                "AuditStaffID",
                "staff_last_name",
                "staff_first_name",
                "staff_email",
            ],
        )
        staff_df = pd.concat([staff_df, json_normalize(staff_data)])
        output = output.merge(staff_df, how="left", on="AuditStaffID")

        return output

    def get_all_participants(self, start_date, end_date):
        data = []
        for site_id in self.get_sites():
            self.login_site(site_id)
            data.append(self.get_participants(start_date, end_date))
        return pd.concat(data)


def parse_date(datestring):  # for .Net json tic crappiness
    timepart = datestring.split("(")[1].split(")")[0]
    milliseconds = int(timepart[:-5])
    hours = int(timepart[-5:]) / 100
    time = milliseconds / 1000
    dt = pd.to_datetime(datetime.utcfromtimestamp(time + hours * 3600))
    return dt
