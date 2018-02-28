import copy
import pyodbc


STUDENTS_TABLE = 'students_new'
RANDOMIZER_TABLE = 'randomizer_new'
STATUS_TABLE = 'status_new'


def get_connection(config):
  config = copy.copy(config)
  config['uid'] = config['username']
  config['pwd'] = config['password']
  del config['username']
  del config['password']
  return pyodbc.connect(**config)


def insert_student(curs, *args):
  """
  Insert a student into the students table.
  """
  curs.execute(f"""
    INSERT INTO {STUDENTS_TABLE}
      (id, firstname, lastname, address, zipcode,
       guardian_firstname, guardian_lastname, cbo,
       caseworker, school, enrolled_date, is_good_record)
    VALUES
      (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  """, tuple(args))


def insert_randomizer(curs, id, is_treatment):
  """
  Insert a randomization annotation into the randomizer table.
  """
  curs.execute(f"""
    INSERT INTO {RANDOMIZER_TABLE}
      (student_id, is_treatment)
    VALUES
      (?, ?)
  """, (id, is_treatment))


def insert_status(curs, id, status):
  """
  Insert a letter-sent status into the status table.
  """
  curs.execute(f"""
    INSERT INTO {STATUS_TABLE}
      (student_id, status)
    VALUES
      (?, ?)
  """, (id, status))
