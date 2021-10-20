import copy

import pyodbc

STUDENTS_TABLE = "students_new"
RANDOMIZER_TABLE = "randomizer_new"
STATUS_TABLE = "status_new"
JOBS_TABLE = "jobs_new"
MAILINGS_TABLE = "mailings_new"


def get_connection(config):
    config = copy.copy(config)
    config["uid"] = config["username"]
    config["pwd"] = config["password"]
    del config["username"]
    del config["password"]
    return pyodbc.connect(**config)


def _create_table_if_not_exists(curs, table_name, *columns):
    rendered_columns = "\n".join(columns)
    curs.execute(
        f"""
    IF NOT EXISTS (
      SELECT * FROM sysobjects WHERE name = '{table_name}' AND xtype = 'U'
    )
    CREATE TABLE {table_name} (
      {rendered_columns}
    )
  """
    )


def insert_student(curs, *args):
    curs.execute(
        f"""
        INSERT INTO {STUDENTS_TABLE}
            (id, firstname, lastname, address, zipcode,
             guardian_firstname, guardian_lastname, cbo,
             caseworker, school, enrolled_date, is_good_record)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        tuple(args),
    )


def insert_randomizer(curs, id, is_treatment):
    curs.execute(
        f"""
        INSERT INTO {RANDOMIZER_TABLE}
            (student_id, is_treatment)
        VALUES
            (?, ?)
    """,
        (id, is_treatment),
    )


def insert_status(curs, id, status):
    curs.execute(
        f"""
        INSERT INTO {STATUS_TABLE}
            (student_id, status)
        VALUES
            (?, ?)
    """,
        (id, status),
    )


def insert_job(curs, job_id, student_id):
    curs.execute(
        f"""
    INSERT INTO {JOBS_TABLE}
      (id, student_id)
    VALUES
      (?, ?)
    """,
        (job_id, student_id),
    )


def insert_mailing(curs, job_id, status, status_datetime):
    curs.execute(
        f"""
    INSERT INTO {MAILINGS_TABLE}
      (job_id, status, status_datetime)
    VALUES
      (?, ?, ?)
    """,
        (job_id, status, status_datetime),
    )
