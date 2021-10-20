import time
import uuid
from datetime import datetime, timedelta

import click
import numpy as np
import pandas as pd
import yaml

from suso import click2mail
from suso import database as db
from suso import email, eto, render


class Submitter:
    def __init__(self, client, data, pdf_directory):
        self.client = client
        self.data = data
        self.keys = list(data)
        self.i = 0
        self.pdf_directory = pdf_directory

    def __len__(self):
        return len(self.data)

    @property
    def key(self):
        return self.keys[self.i]

    def post(self):
        print(f"Posting {self.key}")
        self.document_id = self.client.post_document(
            f"{self.pdf_directory}/{self.key}.pdf"
        )
        datum = self.data[self.key]
        address = {
            "firstname": datum["guardian"],
            "lastname": "",
            "address": datum["address"],
            "city": "Washington",
            "state": "DC",
            "zipcode": datum["zipcode"],
        }
        self.address_list_id = self.client.post_recipients([address], uuid.uuid4())
        self.job_id = self.client.create_job(self.document_id, self.address_list_id)
        self.client._post(
            "jobs",
            self.job_id,
            "update",
            data={
                "rtnName": "Michelle Garcia",
                "rtnAddress2": "1350 Pennsylvania Avenue NW Suite 533",
                "rtnAddress1": "c/o Donald Braman",
                "rtnZip": "20004",
                "rtnCity": "Washington",
                "rtnState": "DC",
            },
        )

    def get_proof(self, tempfile="hold.pdf"):
        r = self.client._post("jobs", self.job_id, "proof")
        self.proof_id = click2mail._get_id_from_response(r)
        r = self.client._get("jobs", self.job_id, "proof", self.proof_id)
        with open(tempfile, "wb") as f:
            f.write(r.content)

    def submit(self):
        self.client.submit_job(str(self.job_id))

    def advance(self):
        self.i += 1


def today():
    return datetime.now().strftime("%Y-%m-%d %H:00")


def get_stats_tables(curs):
    min_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-01")
    curs.execute(
        """
    WITH by_month AS (
      SELECT DATEPART(year, enrolled_date) as the_year,
             DATEPART(month, enrolled_date) the_month
        FROM students_new
       WHERE enrolled_date >= ?
    )
    SELECT the_year, the_month, COUNT(*)
      FROM by_month
     GROUP BY the_year, the_month
     ORDER BY the_year, the_month ASC;
    """,
        (min_date,),
    )
    month_counts = pd.DataFrame.from_records(
        curs.fetchall(), columns=["year", "month", "count"]
    )

    min_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    curs.execute(
        """
    SELECT enrolled_date, COUNT(*)
      FROM students_new
     WHERE enrolled_date >= ?
     GROUP BY enrolled_date
     ORDER BY enrolled_date ASC;
  """,
        (min_date,),
    )
    day_counts = pd.DataFrame.from_records(curs.fetchall(), columns=["day", "count"])

    return "Count of students by month\n\n{}\n\nCount of students by day\n\n{}".format(
        month_counts.to_string(index=False), day_counts.to_string(index=False)
    )


def stop_email(username, key, curs):
    client = email.get_client(username, key)
    text = "There were no new letters at this time\n\n" + get_stats_tables(curs)
    email.send_email(client, "SUSO " + today(), text)


def success_email(username, key, curs, num_sent, num_errors):
    client = email.get_client(username, key)
    text = (
        "There were {} letters sent at this time and there were {} errors\n\n{}".format(
            num_sent, num_errors, get_stats_tables(curs)
        )
    )
    email.send_email(client, "SUSO " + today(), text)


@click.group()
def cli():
    pass


@cli.command("create")
@click.argument("config")
def create_command(config):
    """Setup the tables for the SUSO database"""
    with open(config) as f:
        config = yaml.load(config)

    conn = db.get_connection(config["db"])
    curs = conn.cursor()
    db._create_table_if_not_exists(
        curs,
        db.STUDENTS_TABLE,
        "id INTEGER PRIMARY KEY",
        "firstname NVARCHAR(1024)",
        "lastname NVARCHAR(1024)",
        "address NVARCHAR(1024)",
        "zipcode NVARCHAR(20)",
        "guardian_firstname NVARCHAR(1024)",
        "guardian_lastname NVARCHAR(1024)",
        "cbo NVARCHAR(1024)",
        "caseworker NVARCHAR(1024)",
        "school NVARCHAR(1024)",
        "enrolled_date NVARCHAR(1024)",
        "is_good_record BIT",
        "created_at DATETIME NOT NULL DEFAULT GETDATE()",
    )
    db._create_table_if_not_exists(
        curs,
        db.RANDOMIZER_TABLE,
        "student_id INTEGER PRIMARY KEY",
        "is_treatment BIT",
        "created_at DATETIME NOT NULL DEFAULT GETDATE()",
    )
    db._create_table_if_not_exists(
        curs,
        db.STATUS_TABLE,
        "id INTEGER IDENTITY(1, 1) PRIMARY KEY",
        f"student_id INTEGER FOREIGN KEY REFERENCES {db.STUDENTS_TABLE}(id)",
        "status NVARCHAR(20)",
        "created_at DATETIME NOT NULL DEFAULT GETDATE()",
    )
    db._create_table_if_not_exists(
        curs,
        db.JOBS_TABLE,
        "id INTEGER PRIMARY KEY NOT NULL",
        f"student_id INTEGER FOREIGN KEY REFERENCES {db.STUDENTS_TABLE}(id)",
        "created_at DATETIME NOT NULL DEFAULT GETDATE()",
    )
    db._create_table_if_not_exists(
        curs,
        db.MAILINGS_TABLE,
        "id INTEGER IDENTITY(1, 1) PRIMARY KEY, NOT NULL",
        f"job_id INTEGER FOREIGN KEY REFERENCES {db.JOBS_TABLE}(id)",
        "status NVARCHAR(64)",
        "status_datetime DATETIME",
        "created_at DATETIME NOT NULL DEFAULT GETDATE()",
    )

    # This sets a starting point in the database
    db.insert_student(
        curs,
        1,
        "First",
        "Last",
        "Address",
        "Zip",
        "GFirst",
        "GLast",
        "Fake CBO",
        "Fake Caseworker",
        "Fake School",
        "2018-01-08",
        0,
    )
    db.insert_randomizer(curs, 1, 0)
    curs.close()
    conn.commit()
    conn.close()


@cli.command("run")
@click.argument("config")
@click.option("--tex", "-t", default="./tex", help="Where to store generated tex files")
@click.option("--pdf", "-p", default="./pdf", help="Where to store generated pdf files")
def run_command(config, tex, pdf):
    with open(config) as f:
        config = yaml.load(f)

    # From what date should we pull new data from ETO?
    conn = db.get_connection(config["db"])
    curs = conn.cursor()
    curs.execute(f"""SELECT MAX(enrolled_date) FROM {db.STUDENTS_TABLE}""")
    start_date = max(curs.fetchall()[0][0], "2018-01-04")  # Deal with start date

    # Back the date up a couple days in case something happened to time zones or automation
    start_date = (
        datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=2)
    ).strftime("%Y-%m-%d")

    curs.execute(f"""SELECT id FROM {db.STUDENTS_TABLE}""")
    all_ids = {row[0] for row in curs.fetchall()}
    curs.close()

    # Setup ETO handler
    api = eto.ApiHandler()
    api.login(config["eto"]["username"], config["eto"]["password"])

    # Pull data from ETO
    click.echo("Pulling data from ETO")
    end_date = datetime.now().strftime("%Y-%m-%d")
    potential_participants = api.get_all_participants(start_date, end_date)
    potential_participants[
        "referral_date"
    ] = potential_participants.ProgramStartDate.apply(eto.convert_date)

    # Filter to new participants
    new_participants = potential_participants[
        ~potential_participants.CLID.isin(all_ids)
    ]
    new_participants = new_participants.sort_values(by="referral_date", ascending=False)
    new_participants = new_participants.drop_duplicates("CLID")

    # Filter for missing data
    bad_data_filter = (
        new_participants.guardian_firstname.isnull()
        | new_participants.guardian_lastname.isnull()
        | new_participants.FName.isnull()
        | new_participants.LName.isnull()
        | new_participants.address.isnull()
        | new_participants.zipcode.isnull()
    )
    good_participants = new_participants[~bad_data_filter]
    bad_participants = new_participants[bad_data_filter]

    # Commit participants to db
    click.echo("Committing participants to db")
    curs = conn.cursor()
    for df, is_good_record in [[good_participants, 1], [bad_participants, 0]]:
        for _, row in df.iterrows():
            if pd.isnull(row.staff_first_name) or pd.isnull(row.staff_last_name):
                caseworker_name = None
            else:
                caseworker_name = " ".join((row.staff_first_name, row.staff_last_name))
            db.insert_student(
                curs,
                row.CLID,
                row.FName,
                row.LName,
                row.address,
                row.zipcode,
                row.guardian_firstname,
                row.guardian_lastname,
                row.site_name,
                caseworker_name,
                row.school_name,
                row.referral_date,
                is_good_record,
            )

    curs.close()
    conn.commit()

    # Pull standardized participant data from db
    click.echo("Getting standardized participant list")
    curs = conn.cursor()
    curs.execute(
        f"""
    SELECT s.id, s.firstname, s.lastname, s.address, s.zipcode,
           s.guardian_firstname, s.guardian_lastname,
           s.cbo, s.caseworker, s.enrolled_date,
           s.school, r.is_treatment
      FROM {db.STUDENTS_TABLE} s
    LEFT JOIN {db.RANDOMIZER_TABLE} r
        ON s.id = r.student_id
     WHERE r.is_treatment IS NULL
       AND s.is_good_record = 1
  """
    )
    df = pd.DataFrame.from_records(
        curs.fetchall(),
        columns=[
            "id",
            "firstname",
            "lastname",
            "address",
            "zipcode",
            "guardian_firstname",
            "guardian_lastname",
            "cbo",
            "caseworker",
            "enrolled_date",
            "school",
            "is_treatment",
        ],
    )
    curs.close()

    # Pull total number of students randomized so far
    curs = conn.cursor()
    total_seen = curs.execute(
        f"""SELECT COUNT(*) FROM {db.RANDOMIZER_TABLE}"""
    ).fetchall()[0][0]
    curs.close()

    # Randomize students
    if len(df) != 0:
        click.echo("Randomizing")
        df = df.sample(frac=1)
        df["is_treatment"] = ((np.arange(len(df)) + total_seen) % 2).astype(bool)

        # Record randomizations
        curs = conn.cursor()
        for _, row in df.iterrows():
            db.insert_randomizer(curs, row.id, 1 if row.is_treatment else 0)
        curs.close()
        conn.commit()
    else:
        click.echo("Nothing to randomize. Perhaps there are things to send?")

    # Get unsubmitted treatment students from database
    curs = conn.cursor()
    curs.execute(
        f"""
    WITH successes (student_id, status) AS (
      SELECT student_id, status FROM {db.STATUS_TABLE} WHERE status = 'Success'
    ),
    successful_students (student_id, status) AS (
      SELECT DISTINCT student_id, status FROM successes
    )
    SELECT s.id, s.firstname, s.lastname, s.address, s.zipcode,
           s.guardian_firstname, s.guardian_lastname,
           s.cbo, s.caseworker, s.enrolled_date,
           s.school, r.is_treatment
      FROM {db.STUDENTS_TABLE} s
      JOIN {db.RANDOMIZER_TABLE} r
        ON s.id = r.student_id
      LEFT JOIN successful_students st
        ON s.id = st.student_id
     WHERE r.is_treatment = 1
       AND s.is_good_record = 1
       AND st.status IS NULL
  """
    )
    df = pd.DataFrame.from_records(
        curs.fetchall(),
        columns=[
            "id",
            "firstname",
            "lastname",
            "address",
            "zipcode",
            "guardian_firstname",
            "guardian_lastname",
            "cbo",
            "caseworker",
            "enrolled_date",
            "school",
            "is_treatment",
        ],
    )
    curs.close()

    if len(df) == 0:
        click.echo("Nothing to send. Quitting")
        curs = conn.cursor()
        stop_email(config["mailchimp"]["username"], config["mailchimp"]["key"], curs)
        curs.close()
        conn.close()
        return
    else:
        click.echo(f"We have {len(df)} letters to send!")

    # Fix known errors
    click.echo("Fixing errors")
    df.loc[
        df.caseworker.str.startswith("User") & df.cbo.str.startswith("Far South"),
        "caseworker",
    ] = render.CBOs["Far Southeast"].default_contact
    df["caseworker"] = df.caseworker.map(
        lambda word: "".join(letter for letter in word if not letter.isdigit()),
        na_action="ignore",
    )

    # Render pdfs
    click.echo("Rendering pdfs")
    data = {
        row.id: {
            "cbo_name": row.cbo,
            "school": row.school,
            "guardian": row.guardian_firstname + " " + row.guardian_lastname,
            "caseworker_name": row.caseworker,
            "address": row.address,
            "zipcode": row.zipcode,
        }
        for _, row in df.iterrows()
        if row.is_treatment > 0
    }

    render.render_templates(data, output_directory=tex, pdf_output_directory=pdf)

    # Ship things to click2mail
    click.echo("Shipping things to click2mail")
    client = click2mail.Click2MailClient(is_production=True)
    client.login(config["click2mail"]["username"], config["click2mail"]["password"])
    client._post("account", "authorize")

    client.set_return_address(
        "Don Braman",
        "Office of the City Administrator",
        "1350 Pennsylvania Avenue NW Suite 533",
        "Washington",
        "DC",
        "20004",
    )

    submitter = Submitter(client, data, pdf_directory=pdf)

    curs = conn.cursor()
    num_success = num_error = 0
    for i in range(len(submitter)):
        click.echo(f"On {i+1} of {len(submitter)}")
        submitter.post()
        db.insert_job(curs, submitter.job_id, submitter.key)
        time.sleep(1)
        try:
            submitter.submit()
            success = True
        except Exception:
            success = False
        db.insert_status(curs, submitter.key, "Success" if success else "Error")
        num_success += 1 if success else 0
        num_error += 1 if not success else 0
        submitter.advance()
        conn.commit()
        time.sleep(1)

    curs.close()

    click.echo(
        "Done submitting to click2mail; {} submitted and {} errors".format(
            num_success, num_error
        )
    )

    curs = conn.cursor()
    success_email(
        config["mailchimp"]["username"],
        config["mailchimp"]["key"],
        curs,
        num_success,
        num_error,
    )
    curs.close()
    conn.close()


@cli.command("mailing")
@click.argument("config")
def mailing_status_command(config):
    with open(config) as f:
        yaml.load(config)
    conn = db.get_connection(config["db"])
    curs = conn.cursor()

    click.echo("Getting old mailings")
    curs.execute(
        f"""
    SELECT j.id, s.id
      FROM {db.STUDENTS_TABLE} s
      JOIN {db.JOBS_TABLE} j
        ON s.id = j.student_id
      LEFT JOIN {db.MAILINGS_TABLE} m
        ON j.id = m.job_id
     WHERE NOT (m.status = 'Arrived at Recipient PO' OR 'USPS Indicated Delievered')
  """
    )
    returned = curs.fetchall()
    for job_id, student_id in returned:
        status, status_time = client.get_tracking_data(job_id)
        if not status:
            continue
        status_time = datetime.strptime(status_time[:-2], "%Y-%m-%d %H:%M:%S")
        db.insert_mailing(curs, job_id, status, status_time)
    curs.close()
    conn.commit()
    conn.close()


if __name__ == "__main__":
    cli()
