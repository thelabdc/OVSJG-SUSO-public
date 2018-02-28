import glob
import os
import re
import shutil
import subprocess
from collections import namedtuple

import jinja2


TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
IMAGE_DIR = os.path.join(TEMPLATE_DIR, 'images')

CBO = namedtuple('CBO', ('fullname', 'address', 'zipcode', 'phone', 'image', 'default_contact'))

CBOs = {
  'Example': CBO(
    fullname='Example CBO DC',
    address='1350 Pennsylvania Avenue NW',
    zipcode='20004',
    phone='202-555-1234',
    image='dcps.png',
    default_contact='John Smith'
  )
}


SCHOOL_TO_IMAGE = {
  'Example': 'dcps.png'
}


def get_address_from_cbo_name(name):
  return CBOs[name].address


def get_fullname_from_cbo_name(name):
  return CBOs[name].fullname


def get_official_school_name(school_name):
  """
  Translate ETO's school names to readable names. If None,
  or not in SCHOOL_TO_IMAGE just return DCPS

  Args:
    school_name (str): The school name from ETO

  Returns:
    str: Either DCPS, a standardized version of a DCPS school name,
      or a name from SCHOOL_TO_IMAGE
  """
  if not school_name:
    return 'DCPS'

  if 'kipp' in school_name.lower():
    return 'KIPP DC'

  #from IPython.core.debugger import Tracer; Tracer()()
  match = re.match(r'^(.*)(PCS|EC|ES|MS|HS).*$', school_name)
  if match:
    if match.groups()[1] == 'PCS':
      school_name = match.groups()[0]
    elif match.groups()[1] == 'EC':
      school_name = f'{match.groups()[0].strip()} Educational Campus'
    elif match.groups()[1] == 'ES':
      school_name = f'{match.groups()[0].strip()} Elementary School'
    elif match.groups()[1] == 'MS':
      school_name = f'{match.groups()[0].strip()} Middle School'
    elif match.groups()[1] == 'HS':
      school_name = f'{match.groups()[0].strip()} High School'

  for school in SCHOOL_TO_IMAGE:
    if school_name.startswith(school):
      return school

  return school_name


def get_zipcode_from_cbo_name(name):
  return CBOs[name].zipcode


def get_phone_from_cbo_name(name):
  return CBOs[name].phone


def get_image_from_cbo_name(name, image_dir):
  return os.path.join(os.path.relpath(IMAGE_DIR, image_dir), CBOs[name].image)


def get_image_from_school_name(name, image_dir):
  return os.path.join(os.path.relpath(IMAGE_DIR, image_dir), SCHOOL_TO_IMAGE.get(name, 'dcps.png'))


def get_default_contact_from_cbo_name(name):
  return CBOs[name].default_contact


def get_latex_env(template_dir=TEMPLATE_DIR):
  """
  Return a jinja env which will work properly with LaTeX. Assumes you want
  to load the templates from the filesystem, with the templates located
  at `template_dir`.

  Args:
    template_dir (str): The template directory

  Returns:
    jinja2.Environment: The LaTeX-worthy Jinja2 environment
  """
  return jinja2.Environment(
    block_start_string='\BLOCK{',
    block_end_string='}',
    variable_start_string= '\VAR{',
    variable_end_string='}',
    comment_start_string='\#{',
    comment_end_string='}',
    line_statement_prefix='%%',
    line_comment_prefix='%#',
    trim_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader(template_dir)
  )


def render_templates(data, output_directory, template_name='template.tex.j2',
  pdf_output_directory=None, cleanup=True):
  """
  Render a single template (named `template_name`), which is in `template_dir`
  multiple times according to the dictionary `data`. The output will be stored in
  `output_directory` by the name {key}.tex where the keys iterate over the keys of
  data.

  Finally, this will also run pdflatex on the output tex files and leave pdfs in the
  output directory as well.

  Args:
    template_dir (str): The template directory
    data (dict[str, dict[str, str]]): The dictionary from filename to the keys to
      fill in in the template
    output_directory (str): Where to store the rendered templates and pdfs
    template_name (str): The name of the template to render
    pdf_output_directory (str|None): If passed, will move rendered pdfs
      to this directory
    cleanup (bool): If True, will remove tex cruft from rendering

  Side effects:
    Creates many files on the hard drive in `output_directory`
  """
  env = get_latex_env()
  template = env.get_template(template_name)

  if not os.path.exists(output_directory):
    os.makedirs(output_directory)

  if pdf_output_directory and not os.path.exists(pdf_output_directory):
    os.makedirs(pdf_output_directory)

  # Write all the templates
  templates_rendered = []
  for key, datum in data.items():

    # If there is no CBO, just ignore it
    if not datum['cbo_name']:
      continue
    templates_rendered.append(key)

    # Render the template in memory
    cbo_name = datum['cbo_name']
    # from IPython.core.debugger import Tracer; Tracer()()
    school_name = get_official_school_name(datum.get('school'))
    rendered = template.render(school_image=get_image_from_school_name(school_name, output_directory),
                               cbo_image=get_image_from_cbo_name(cbo_name, output_directory),
                               cbo_address=get_address_from_cbo_name(cbo_name),
                               cbo_zipcode=get_zipcode_from_cbo_name(cbo_name),
                               contact_number=get_phone_from_cbo_name(cbo_name),
                               cbo_name=get_fullname_from_cbo_name(cbo_name),
                               caseworker_name=datum['caseworker_name'] or get_default_contact_from_cbo_name(cbo_name),
                               guardian=datum['guardian'],
                               school=school_name)

    # Write the template out to disk
    with open(os.path.join(output_directory, '{key}.tex'.format(key=key)), 'w') as f:
      f.write(rendered)

  # Render all the pdfs
  for key in data:
    p = subprocess.Popen(['pdflatex', '{key}'.format(key=key)], cwd=output_directory)
    p.wait()
    if p.returncode:
      raise EnvironmentError("Something went wrong rendering template {key}".format(key=key))

    # If passed, separate out the pdfs
    if pdf_output_directory:
      pdf_name = '{}.pdf'.format(key)
      shutil.move(os.path.join(output_directory, pdf_name),
                  os.path.join(pdf_output_directory, pdf_name))

    # If asked, clean up the tex output
    if cleanup:
      # Delete all non-tex files
      for filename in glob.glob(os.path.join(output_directory, '{}.*'.format(key))):
        if not (filename.endswith('.tex') or filename.endswith('.pdf')):
          os.remove(filename)
