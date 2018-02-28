import glob
import os
import tempfile

from suso import render


def test_render_templates():
  the_vars = {
    'guardian': 'Kevin Wilson',
    'caseworker_name': 'Peter Casey',
    'cbo_address': '1350 Pennsylvania Avenue',
    'cbo_zip': '20004',
    'cbo_name': 'Awesome Helpers',
    'school': 'Simple Elementary School',
    'contact_number': '(202) 555-1234'
  }

  with tempfile.TemporaryDirectory() as tex_dir, \
      tempfile.TemporaryDirectory() as pdf_dir:

    # Render the templates
    render.render_templates({'kevin': the_vars}, tex_dir,
                            pdf_output_directory=pdf_dir)

    # There should have been exactly one
    tex_files = glob.glob(os.path.join(tex_dir, '*.tex'))
    pdf_files = glob.glob(os.path.join(pdf_dir, '*.pdf'))
    assert len(tex_files) == 1
    assert len(pdf_files) == 1

    # Named by the relevant key
    assert tex_files[0].endswith('kevin.tex')
    assert pdf_files[0].endswith('kevin.pdf')
