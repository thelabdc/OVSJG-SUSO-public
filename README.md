# OVSJG-SUSO

Analyses related to the SUSO CBO Outreach Support Project

## Automation

Much of this repository is dedicated to the automation of the letter sending process.
In order to get that going, run

```
poetry install
```

You will then find the command `susocli` on your path. That command requires a config
file, a template of which can be found in `config.template.yml`. You'll need to fill that
out.

**WARNING** The Dockerfile is currently out of date with the migration to poetry. To
fix you'll need to install poetry in the Dockerfile and use `poetry install` instead
of `pip -r install requirements.txt` and similarly change the commands below to
`poetry run susocli` instead of simply `susocli`.

The automation aspect of this is handled by the `Dockerfile`. This is run on a the
ktensor box (10.56.6.64) as the following cron job:

```
0 19-23 * * 1-5 docker run --rm -v /mnt/dockervols/suso:/work thelabdc/ovsjg-suso susocli run /suso/config.yml -t /work/tex -p /work/pdf >> /mnt/dockervols/suso/log 2>&1
1 0 * * 2-6 docker run --rm -v /mnt/dockervols/suso:/work thelabdc/ovsjg-suso susocli run /suso/config.yml -t /work/tex -p /work/pdf >> /mnt/dockervols/suso/log 2>&1
31 0 * * 2-6 docker run --rm -v /mnt/dockervols/suso:/work thelabdc/ovsjg-suso susocli run /suso/config.yml -t /work/tex -p /work/pdf >> /mnt/dockervols/suso/log 2>&1
```

Though note that the first time you run `susocli` you'll need to have run `susocli create` to create the relevant database tables.


# Order to run for attendance analyses

If you wish to run the attendance analysis front to back you can do so by first
installing all required dependencies thus:

```bash
poetry install
Rscript -e 'renv::restore()'
```

If you do not have `renv` and `poetry` installed, these commands will provide them:

```bash
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -
Rscript -e 'if(!requireNamespace("remotes")){install.packages("remotes");remotes::install_github("rstudio/renv")} else {remotes::install_github("rstudio/renv")}'
```

Once these are installed, you will need the files enumerated in `required_data.txt`.
If you are a member of The Lab @ DC, you should be able to find them in our long term
storage. If you are not a member of The Lab @ DC, please contact `thelab@dc.gov`, though note that access to these data are restricted by agreements with our project partners.

Once these files are in place, you can run:

```bash
make all
```

The outputs of all scripts will be placed in the `output` directory. The following
notes detail exactly what each script does.

## Pull, clean, and merge data (src/notebooks/100_pull_and_clean_data)

These files require access to The Lab's OSSE-wide attendance data files for SY 16-17 (pre-intervention year) and SY 17-18 (intervention year). Please note that the data associated with this project is considered highly sensitive.
Any researcher wanting to rerun these analyses should contact The Lab @ DC at
thelab@dc.gov to discuss potential data sharing agreements.

1. [015_convert_to_parquet.ipynb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/notebooks/100_pull_and_clean_data/015_convert_to_parquet.ipynb)

  - _Takes in_:
    - Zipped attendance files for DCPS and PCS for 16-17 and 17-18

  - _What it does_:
    - Converts to parquet format

  - _Outputs_:
    - Parquet format attendance files for DCPS and PCS for 16-17 and 17-18

2. [020_createlookuptable_suso_osse.ipynb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/notebooks/100_pull_and_clean_data/020_createlookuptable_suso_osse.ipynb)

  - _Takes in_:
    - Data on SUSO participants: created as part of [010_merge_and_wrangle_suso.ipynb](https://github.com/thelabdc/OVSJG-SUSO/blob/master/src/notebooks/100_pull_and_clean_data/010_merge_and_wrangle_suso.ipynb)
    - Parquet attendance files created in previous script

  - _What it does_:
    - Reads in data from SUSO randomization
    - Reads in student attributes from OSSE (e.g. student name; dob)
    - First tries exact matches on cleaned names and date of birth
    - Then uses fuzzy matching to do approximate matches (usually due to name mispelling)

  - _Outputs_:
    - lookup_suso_osse: a table stored in the database with a student's suso id, his or her OSSE ID (USI), and whether exact or fuzzy match; used in next script to subset long-form OSSE attendance data (student-day) to SUSO students

3. [030_attendance_cleaning.ipynb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/notebooks/100_pull_and_clean_data/030_attendance_cleaning.ipynb)

  - _Takes in_:
    - lookup_osse_suso: lookup table that has USIs (osse attendance data unique identifiers) for those referred to suso

  - _What it does_:
    - For present and previous school year, constructs daily tallies of different types of absences and whether student is truant at that date (10 or more unexcused) and/or chronically absent at that date (absent, either excused or unexcused, for more than 10% of school attendance days)

  - _Outputs_: parquet files used in subsequent scripts
    - dcps_sy1718_attendanceoutcomes_suso: used for intervention year analysis
    - charter_sy1617_attendanceoutcomes_suso: used for PAP baselines
    - dcps_sy1718_attendanceoutcomes_suso: used for intervention year analysis
    - charter_sy1617_attendanceoutcomes_suso: used for PAP baselines

4. [040_descriptives_previoussy_forPAP.ipynb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/notebooks/100_pull_and_clean_data/040_descriptives_previoussy_forPAP.ipynb)

 - _Takes in_:
    - Tables from previous script: dcps/charter_sy1617...
    - Geojson files that have lat/long of schools
    - DC open data geojson file of DC census tract demographics

  - _What it does_:
    - Descriptives on attendance outcomes at end of school year
    - Map truancy rates by school

  - _Outputs_: figures for pre-analysis plan and "background" section of writeup

5. [050_cleanstudents_whoswitchsystems.ipynb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/notebooks/100_pull_and_clean_data/050_cleanstudents_whoswitchsystems.ipynb)

 - _Takes in_:
    - Tables attendance_cleaning_sql that reflect SUSO year attendance: dcps/charter_sy1718

 - _What it does_:
    - Identifies students who are in both dcps and charter schools at some point during the year
    - Checks whether those students' attendance is accurately recorded in following file created in previous script `attendance_both_clean.parquet`



## Descriptive Analyses (src/notebooks/200_descriptives)

These notebooks provide the descriptive analyses that appear in the report.

1. [060_sample_descriptives.ipynb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/notebooks/200_descriptives/060_sample_descriptives.ipynb)

- _Takes in_:
    - Parquet files of all DCPS and PCS students in SY 17-18
    - Lookup table (`suso_osse_lookup.pkl`) and merged OSSE-SUSO data indicating randomization status (`df_suso_merged.csv`)

- _What it does_:
   - Summarizes descriptive characteristics for three groups of students: (1) students in SUSO schools but not in sample, (2) students in SUSO schools and in sample, (3) students not in SUSO schools
    - Summarizes balance across treatment and control groups

- _Outputs_: figures for writeup saved in `output`

2. [070_attendance_descriptives.ipynb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/notebooks/200_descriptives/070_attendance_descriptives.ipynb)

- _Takes in_: data created in earlier scripts
    - Attendance end-of-year outcomes: attendance_eoy_wsuso.pkl
    - SUSO data: df_suso_merged.csv
    - Attendance daily outcomes: attendance_both_clean.pkl

- _What it does_:
   - Finds the start dates for the different clocks (7 days post-referral versus observed delivery date)
   - For delivery date clock, matches control group students with nearest-referral tx student
   - Using the different clocks, calculates changes in absences from start of clock to two calendar weeks after the end of the clock

- _Outputs_:
    - figures for writeup
    - attendance_readyforAB.pkl
    - attendance_readyforregressions.csv

## Conduct A/B testing and regression analyses (src/notebooks/300_analysis)

These scripts actually perform the analysis on the data that we have generated for the
SUSO project. If you have a copy of the data generated in the previous scripts, then
you should be able to run these files front to back.

1. [080_attendance_ABtests.ipynb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/notebooks/300_analysis/080_attendance_ABtests.ipynb)

- _Takes in_:
    - attendance_readyforAB.pkl (created in previous script)

- _What it does_:
    -Conduct A/B tests described in pre-analysis plan
    -Plots distribution of pr(treat > control) (or vice versa) over draws

- _Outputs_: figures for writeup and attendanceoutcomes_posteriors_toplot.csv used in next script

2. [090_analyze_engagement.ipynb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/notebooks/300_analysis/090_analyze_engagement.ipynb)

Original notebook for analyzing impact on family engagement.

## Visualize results and R-based regression robustness (src/R/400_additional_plots)

1. [100_attendance_ABtests_additionalplots.Rmdb](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/R/400_additional_plots/100_attendance_ABtests_additionalplots.Rmd)

- _Takes in_:
    -  attendanceoutcomes_posteriors_toplot.csv

- _What it does_:
    - Plots posterior differences in outcomes between treatment and control (want to skew away from 0)

- _Outputs_: figures for writeup


2. [110_attendance_regressionrobustness.Rmd](https://github.com/thelabdc/OVSJG-SUSO-public/blob/master/src/R/400_additional_plots/110_attendance_regressionrobustness.Rmd)

- _Takes in_:
    -  attendance_readyforregressions.csv

- _What it does_:
    - Regressions as robustness checks on A/B tests (logistic reg for binary with and without covars; linear and negative binomial for count outcomes)

- _Outputs_: figures and tables for writeup; tables are latex via stargazer and then copied to a .tex file





