PY_SRC_DIR=src/notebooks
R_SRC_DIR=src/R/400_additional_plots
OUTPUT_DIR=output
PAPERMILL=poetry run papermill

.PHONY: all

$(OUTPUT_DIR)/100_pull_and_clean_data/015_convert_to_parquet.ipynb: $(PY_SRC_DIR)/100_pull_and_clean_data/015_convert_to_parquet.ipynb
	mkdir -p $(OUTPUT_DIR)/100_pull_and_clean_data
	$(PAPERMILL) $(PY_SRC_DIR)/100_pull_and_clean_data/015_convert_to_parquet.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/015_convert_to_parquet.ipynb

$(OUTPUT_DIR)/100_pull_and_clean_data/020_createlookuptable_suso_osse.ipynb: $(PY_SRC_DIR)/100_pull_and_clean_data/020_createlookuptable_suso_osse.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/015_convert_to_parquet.ipynb
	mkdir -p $(OUTPUT_DIR)/100_pull_and_clean_data
	$(PAPERMILL) $(PY_SRC_DIR)/100_pull_and_clean_data/020_createlookuptable_suso_osse.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/020_createlookuptable_suso_osse.ipynb

$(OUTPUT_DIR)/100_pull_and_clean_data/030_attendance_cleaning.ipynb: $(PY_SRC_DIR)/100_pull_and_clean_data/030_attendance_cleaning.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/020_createlookuptable_suso_osse.ipynb
	mkdir -p $(OUTPUT_DIR)/100_pull_and_clean_data
	$(PAPERMILL) $(PY_SRC_DIR)/100_pull_and_clean_data/030_attendance_cleaning.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/030_attendance_cleaning.ipynb

$(OUTPUT_DIR)/100_pull_and_clean_data/040_descriptives_previoussy_forPAP.ipynb: $(PY_SRC_DIR)/100_pull_and_clean_data/040_descriptives_previoussy_forPAP.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/030_attendance_cleaning.ipynb
	mkdir -p $(OUTPUT_DIR)/100_pull_and_clean_data
	$(PAPERMILL) $(PY_SRC_DIR)/100_pull_and_clean_data/040_descriptives_previoussy_forPAP.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/040_descriptives_previoussy_forPAP.ipynb

$(OUTPUT_DIR)/100_pull_and_clean_data/050_cleanstudents_whoswitchsystems.ipynb: $(PY_SRC_DIR)/100_pull_and_clean_data/050_cleanstudents_whoswitchsystems.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/040_descriptives_previoussy_forPAP.ipynb
	mkdir -p $(OUTPUT_DIR)/100_pull_and_clean_data
	$(PAPERMILL) $(PY_SRC_DIR)/100_pull_and_clean_data/050_cleanstudents_whoswitchsystems.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/050_cleanstudents_whoswitchsystems.ipynb

# Descriptives

$(OUTPUT_DIR)/200_descriptives/060_sample_descriptives.ipynb: $(PY_SRC_DIR)/200_descriptives/060_sample_descriptives.ipynb $(OUTPUT_DIR)/100_pull_and_clean_data/050_cleanstudents_whoswitchsystems.ipynb
	mkdir -p $(OUTPUT_DIR)/200_descriptives
	$(PAPERMILL) $(PY_SRC_DIR)/200_descriptives/060_sample_descriptives.ipynb $(OUTPUT_DIR)/200_descriptives/060_sample_descriptives.ipynb

$(OUTPUT_DIR)/200_descriptives/070_attendance_descriptives.ipynb: $(PY_SRC_DIR)/200_descriptives/070_attendance_descriptives.ipynb $(OUTPUT_DIR)/200_descriptives/060_sample_descriptives.ipynb
	mkdir -p $(OUTPUT_DIR)/200_descriptives
	$(PAPERMILL) $(PY_SRC_DIR)/200_descriptives/070_attendance_descriptives.ipynb $(OUTPUT_DIR)/200_descriptives/070_attendance_descriptives.ipynb

# Analysis

$(OUTPUT_DIR)/300_analysis/080_attendance_ABtests.ipynb: $(PY_SRC_DIR)/300_analysis/080_attendance_ABtests.ipynb $(OUTPUT_DIR)/200_descriptives/070_attendance_descriptives.ipynb
	mkdir -p $(OUTPUT_DIR)/300_analysis
	$(PAPERMILL) $(PY_SRC_DIR)/300_analysis/080_attendance_ABtests.ipynb $(OUTPUT_DIR)/300_analysis/080_attendance_ABtests.ipynb

$(OUTPUT_DIR)/300_analysis/090_analyze_engagement.ipynb: $(PY_SRC_DIR)/300_analysis/090_analyze_engagement.ipynb $(OUTPUT_DIR)/300_analysis/080_attendance_ABtests.ipynb
	mkdir -p $(OUTPUT_DIR)/300_analysis
	$(PAPERMILL) $(PY_SRC_DIR)/300_analysis/090_analyze_engagement.ipynb $(OUTPUT_DIR)/300_analysis/090_analyze_engagement.ipynb


# Plots

$(OUTPUT_DIR)/100_attendance_ABtests_additionalplots.pdf: $(R_SRC_DIR)/100_attendance_ABtests_additionalplots.Rmd $(OUTPUT_DIR)/300_analysis/090_analyze_engagement.ipynb
	Rscript -e 'rmarkdown::render("$(R_SRC_DIR)/100_attendance_ABtests_additionalplots.Rmd")'
	mv $(R_SRC_DIR)/100_attendance_ABtests_additionalplots.pdf $(OUTPUT_DIR)/100_attendance_ABtests_additionalplots.pdf

$(OUTPUT_DIR)/110_attendance_regressionrobustness.pdf: $(R_SRC_DIR)/110_attendance_regressionrobustness.Rmd $(OUTPUT_DIR)/100_attendance_ABtests_additionalplots.pdf
	mkdir -p $(OUTPUT_DIR)/tables
	Rscript -e 'rmarkdown::render("$(R_SRC_DIR)/110_attendance_regressionrobustness.Rmd")'
	mv $(R_SRC_DIR)/110_attendance_regressionrobustness.pdf $(OUTPUT_DIR)/110_attendance_regressionrobustness.pdf

$(OUTPUT_DIR)/120_Rplotting.pdf: $(R_SRC_DIR)/120_Rplotting.Rmd $(OUTPUT_DIR)/110_attendance_regressionrobustness.pdf
	Rscript -e 'rmarkdown::render("$(R_SRC_DIR)/120_Rplotting.Rmd")'
	mv $(R_SRC_DIR)/120_Rplotting.pdf $(OUTPUT_DIR)/120_Rplotting.pdf

all: \
	$(OUTPUT_DIR)/100_pull_and_clean_data/015_convert_to_parquet.ipynb \
	$(OUTPUT_DIR)/100_pull_and_clean_data/020_createlookuptable_suso_osse.ipynb \
	$(OUTPUT_DIR)/100_pull_and_clean_data/030_attendance_cleaning.ipynb \
	$(OUTPUT_DIR)/100_pull_and_clean_data/040_descriptives_previoussy_forPAP.ipynb \
	$(OUTPUT_DIR)/100_pull_and_clean_data/050_cleanstudents_whoswitchsystems.ipynb \
	$(OUTPUT_DIR)/200_descriptives/060_sample_descriptives.ipynb \
	$(OUTPUT_DIR)/200_descriptives/070_attendance_descriptives.ipynb \
	$(OUTPUT_DIR)/100_attendance_ABtests_additionalplots.pdf \
	$(OUTPUT_DIR)/110_attendance_regressionrobustness.pdf \
	$(OUTPUT_DIR)/120_Rplotting.pdf

clean:
	rm -f $(R_SRC_DIR)/*.pdf \
		$(R_SRC_DIR)/*.log \
		$(R_SRC_DIR)/*.tex \
		$(R_SRC_DIR)/*.md \
		$(R_SRC_DIR)/*.html \
		$(R_SRC_DIR)/*.aux \
		$(R_SRC_DIR)/*.synctex.gz \
		$(R_SRC_DIR)/*.toc \
		$(R_SRC_DIR)/*latexmk \
		$(R_SRC_DIR)/*.fls