# Changelog

![DIIVE](images/logo_diive1_256px.png)

## v0.70.1 | 1 Mar 2024

- Updated (and cleaned) notebook `StepwiseMeteoScreeningFromDatabase.ipynb`

## v0.70.0 | 28 Feb 2024

### New features

- In `StepwiseOutlierDetection`, it is now possible to re-run an outlier detection method. The re-run(s)
  would produce flag(s) with the same name(s) as for the first (original) run. Therefore, an integer is added
  to the flag name. For example, if the test z-score daytime/nighttime is run the first time, it produces the
  flag with the name `FLAG_TA_T1_2_1_OUTLIER_ZSCOREDTNT_TEST`. When the test is run again (e.g. with different
  settings) then the name of the flag of this second run is `FLAG_TA_T1_2_1_OUTLIER_ZSCOREDTNT_2_TEST`,
  etc ... The script now checks whether a flag of the same name was already created, in which case an
  integer is added to the flag name. These re-runs are now available in addition to the `repeat=True` keyword.
  (`diive.pkgs.outlierdetection.stepwiseoutlierdetection.StepwiseOutlierDetection.addflag`)
  Example:
    - `METHOD` with `SETTINGS` is applied with `repeat=True` and therefore repeated until no more outliers
      were found with these settings. The name of the flag produced is `TEST_METHOD_FLAG`.
    - Next, `METHOD` is applied again with `repeat=True`, but this time with different `SETTINGS`. Like before,
      the test is repeated until no more outliers were found with the new settings. The name of the flag produced
      is `TEST_METHOD_2_FLAG`.
    - `METHOD` can be re-run any number of times, each time producing a new
      flag: `TEST_METHOD_3_FLAG`, `TEST_METHOD_4_FLAG`, ...
- Added new function to format timestamps to FLUXNET ISO
  format (`YYYYMMDDhhmm`) (`diive.core.times.times.format_timestamp_to_fluxnet_format`)

### Bugfixes

- Refactored and fixed class to reformat data for FLUXNET
  upload (`diive.pkgs.formats.fluxnet.FormatEddyProFluxnetFileForUpload`)
- Fixed `None` error when reading data files (`diive.core.io.filereader.DataFileReader._parse_file`)

### Notebooks

- Updated notebook `FormatEddyProFluxnetFileForUpload.ipynb`

## v0.69.0 | 23 Feb 2024

### New features

- Added new functions to extract info from a binary that was stored as
  integer. These functions convert a subrange of bits from an integer or an integer series to floats with an
  optional gain applied. See docstring of the respective functions for more
  info. (`diive.pkgs.binary.extract.get_encoded_value_from_int`) (`diive.pkgs.binary.extract.get_encoded_value_series`)
- Added new filetype `RECORD_DAT_20HZ` (`diive/configs/filetypes/RECORD_DAT_20HZ.yml`) for eddy covariance
  high-resolution (20Hz) raw data files recorded by the ETH `rECord` logging script.

## v0.68.1 | 5 Feb 2024

- Fixed bugs in `FluxProcessingChain`, flag creation for missing values did not work because of the missing `repeat`
  keyword (`diive.pkgs.fluxprocessingchain.fluxprocessingchain.FluxProcessingChain`)

## v0.68.0 | 30 Jan 2024

### Updates to stepwise outlier detection

Harmonized the way outlier flags are calculated. Outlier flags are all based on the same base
class `diive.core.base.flagbase.FlagBase` like before, but the base class now includes more code that
is shared by the different outlier detection methods. For example, `FlagBase` includes a method that
enables repeated execution of a single outlier detection method multiple times until all outliers
are removed. Results from all iterations are then combined into one single flag.

The class `StepwiseMeteoScreeningDb` that makes direct use of the stepwise outlier detection was
adjusted accordingly.

### Notebooks

- Updated notebook `StepwiseMeteoScreeningFromDatabase.ipynb`

### Removed features

- Removed outlier test based on seasonal-trend decomposition and z-score calculations (`OutlierSTLRZ`).
  The test worked in principle, but at the moment it is unclear how to set reliable parameters. In addition
  the test is slow when used with multiple years of high-resolution data. De-activated for the moment.

## v0.67.1 | 10 Jan 2024

- Updated: many docstrings.

## v0.67.0 | 9 Jan 2024

### Updates to flux processing chain

The flux processing chain was updated in an attempt to make processing more streamlined and easier to follow. One of the
biggest changes is the implementation of the `repeat` keyword for outlier tests. With this keyword set to `True`, the
respective test is repeated until no more outliers can be found. How the flux processing chain can be used is shown in
the updated `FluxProcessingChain`notebook (`notebooks/FluxProcessingChain/FluxProcessingChain.ipynb`).

### New features

- Added new class `QuickFluxProcessingChain`, which allows to quickly execute a simplified version of the flux
  processing chain. This quick version runs with a lot of default values and thus not a lot of user input is needed,
  only some basic settings. (`diive.pkgs.fluxprocessingchain.fluxprocessingchain.QuickFluxProcessingChain`)
- Added new repeater function for outlier detection: `repeater` is wrapper that allows to execute an outlier detection
  method multiple times, where each iteration gets its own outlier flag. As an example: the simple z-score test is run
  a first time and then repeated until no more outliers are found. Each iteration outputs a flag. This is now used in
  the `StepwiseOutlierDetection` and thus the flux processing chain Level-3.2 (outlier detection) and the meteoscreening
  in `StepwiseMeteoScreeningDb` (not yet checked in this update). To repeat an outlier method use the `repeat` keyword
  arg (see the `FluxProcessingChain` notebook for examples).(`diive.pkgs.outlierdetection.repeater.repeater`)
- Added new function `filter_strings_by_elements`: Returns a list of strings from list1 that contain all of the elements
  in list2.(`core.funcs.funcs.filter_strings_by_elements`)
- Added new function `flag_steadiness_horizontal_wind_eddypro_test`: Create flag for steadiness of horizontal wind u
  from the sonic anemometer. Makes direct use of the EddyPro output files and converts the flag to a standardized 0/1
  flag.(`pkgs.qaqc.eddyproflags.flag_steadiness_horizontal_wind_eddypro_test`)

### Changes

- Added automatic calculation of daytime and nighttime flags whenever the flux processing chain is started
  flags (`diive.pkgs.fluxprocessingchain.fluxprocessingchain.FluxProcessingChain._add_swinpot_dt_nt_flag`)

### Removed features

- Removed class `ThymeBoostOutlier` for outlier detection. At the moment it was not possible to get it to work properly.

### Changes

- It appears that the kwarg `fmt` is used slightly differently for `plot_date` and `plot` in `matplotlib`. It seems it
  is always defined for `plot_date`, while it is optional for `plot`. Now using `fmt` kwarg to avoid the warning:
  *UserWarning: marker is redundantly defined by the 'marker' keyword argument and the fmt string "o" (-> marker='o').
  The keyword argument will take precedence.* Therefore using 'fmt="X"' instead of 'marker="X"'. See also
  answer [here](https://stackoverflow.com/questions/69188540/userwarning-marker-is-redundantly-defined-by-the-marker-keyword-argument-when)

### Environment

- Removed `thymeboost`

## v0.66.0 | 2 Nov 2023

### New features

- Added new class `ScatterXY`: a simple scatter plot that supports bins (`core.plotting.scatter.ScatterXY`)

![DIIVE](images/ScatterXY_diive_v0.66.0.png)

### Notebooks

- Added notebook `notebooks/Plotting/ScatterXY.ipynb`

## v0.64.0 | 31 Oct 2023

### New features

- Added new class `DaytimeNighttimeFlag` to calculate daytime flag (1=daytime, 0=nighttime),
  nighttime flag (1=nighttime, 0=daytime) and potential radiation from latitude and
  longitude (`diive.pkgs.createvar.daynightflag.DaytimeNighttimeFlag`)

### Additions

- Added support for N2O and CH4 fluxes during the calculation of the `QCF` quality flag in class `FlagQCF`
- Added first code for USTAR threshold detection for NEE

### Notebooks

- Added new notebook `notebooks/CalculateVariable/Daytime_and_nighttime_flag.ipynb`

## v0.63.1 | 25 Oct 2023

### Changes

- `diive` repository is now hosted on GitHub.

### Additions

- Added first code for XGBoost gap-filling, not production-ready yet
- Added check if enough columns for lagging features in class `RandomForestTS`
- Added more details in report for class `FluxStorageCorrectionSinglePointEddyPro`

### Bugfixes

- Fixed check in `RandomForestTS` for bug in `QuickFillRFTS`: number of available columns was checked too early
- Fixed `QuickFillRFTS` implementation in `OutlierSTLRZ`
- Fixed `QuickFillRFTS` implementation in `ThymeBoostOutlier`

### Environment

- Added new package [xgboost](https://xgboost.readthedocs.io/en/stable/#)
- Updated all packages

## v0.63.0 | 5 Oct 2023

### New features

- Implemented feature reduction (permutation importance) as separate method in `RandomForestTS`
- Added new function to set values within specified time ranges to a constant
  value(`pkgs.corrections.setto_value.setto_value`)
    - The function is now also implemented as method
      in `StepwiseMeteoScreeningDb` (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.correction_setto_value`)

### Notebooks

- Updated notebook `notebooks/GapFilling/RandomForestGapFilling.ipynb`
- Updated notebook `notebooks/GapFilling/QuickRandomForestGapFilling.ipynb`
- Updated notebook `notebooks/MeteoScreening/StepwiseMeteoScreeningFromDatabase.ipynb`

### Environment

- Added new package [SHAP](https://shap.readthedocs.io/en/latest/)
- Added new package [eli5](https://pypi.org/project/eli5/)

### Tests

- Updated testcase for gap-filling with random
  forest (`test_gapfilling.TestGapFilling.test_gapfilling_randomforest`)

## v0.62.0 | 1 Oct 2023

### New features

- Re-implemented gap-filling of long-term time series spanning multiple years, where the model
  to gap-fill a specific year is built from data from the respective year and its two closest
  neighboring years. (`pkgs.gapfilling.randomforest_ts.LongTermRandomForestTS`)

### Bugfixes

- Fixed bug in `StepwiseMeteoScreeningDb` where position of `return` during setup was incorrect

## v0.61.0 | 28 Sep 2023

### New features

- Added function to calculate the daily correlation between two time
  series (`pkgs.analyses.correlation.daily_correlation`)
- Added function to calculate potential radiation (`pkgs.createvar.potentialradiation.potrad`)

### Bugfixes

- Fixed bug in `StepwiseMeteoScreeningDb` where the subclass `StepwiseOutlierDetection`
  did not use the already sanitized timestamp from the parent class, but sanitized the timestamp
  a second time, leading to potentially erroneous and irregular timestamps.

### Changes

- `RandomForestTS` now has the following functions included as methods:
    - `steplagged_variants`: includes lagged variants of features
    - `include_timestamp_as_cols`: includes timestamp info as data columns
    - `add_continuous_record_number`: adds continuous record number as new column
    - `sanitize`: validates and prepares timestamps for further processing
- `RandomForestTS` now outputs an additional predictions column where predictions from
  the full model and predictions from the fallback model are collected
- Renamed function `steplagged_variants` to `lagged_variants` (`core.dfun.frames.lagged_variants`)
- Updated function `lagged_variants`: now accepts a list of lag times. This makes it possible
  to lag variables in both directions, i.e., the observed value can be paired with values before
  and after the actual time. For example, the variable `TA` is the observed value at the current
  timestamp, `TA-1` is the value from the preceding record, and `TA+1` is the value from the next
  record. Using values from the next record can be useful when modeling observations using data
  from a neighboring measurement location that has similar records but lagged in time due to
  distance.
- Updated README

### Tests

- Updated testcase for gap-filling with random
  forest (`test_gapfilling.TestGapFilling.test_gapfilling_randomforest`)

### Notebooks

- Updated `notebooks/MeteoScreening/StepwiseMeteoScreeningFromDatabase.ipynb`

### Additions

- Added more args for better control of `TimestampSanitizer` (`core.times.times.TimestampSanitizer`)
- Refined various docstrings

## v0.60.0 | 17 Sep 2023

### New features

- Added new class for optimizing random forest parameters (`pkgs.gapfilling.randomforest_ts.OptimizeParamsRFTS`)
- Added new plots for prediction error and residuals (`core.ml.common.plot_prediction_residuals_error_regr`)
- Added function that adds a continuous record number as new column in a dataframe. This
  could be useful to include as feature in gap-filling models for long-term datasets spanning multiple years.
  (`core.dfun.frames.add_continuous_record_number`)

### Changes

- When reading CSV files with pandas `.read_csv()`, the arg `mangle_dupe_cols=True`
  was removed because it is deprecated since pandas 2.0 ...
- ... therefore the check for duplicate column names in class `ColumnNamesSanitizer`
  has been refactored. In case of duplicate columns names, an integer suffix is added to
  the column name. For example: `VAR` is renamed to `VAR.1` if it already exists in the
  dataframe. In case `VAR.1` also already exists, it is renamed to `VAR.2`, and so on.
  The integer suffix is increased until the variable name is unique. (`core.io.filereader.ColumnNamesSanitizer`)
- Similarly, when reading CSV files with pandas `.read_csv()`, the arg `date_parser` was
  removed because it is deprecated since pandas 2.0. When reading a CSV, the arg `date_format`
  is now used instead. The input format remains unchanged, it is still a string giving the datetime
  format, such as `"%Y%m%d%H%M"`.
- The random feature variable is now generated using the same random state as the
  model. (`pkgs.gapfilling.randomforest_ts.RandomForestTS`)
- Similarly, `train_test_split` is now also using the same random state as the
  model. (`pkgs.gapfilling.randomforest_ts.RandomForestTS`)

### Notebooks

- Added new notebook `notebooks/GapFilling/RandomForestParamOptimization.ipynb`

### Tests

- Added testcase for loading dataframe from parquet file (`test_loaddata.TestLoadFiletypes.test_exampledata_parquet`)
- Added testcase for gap-filling with random forest (`test_gapfilling.TestGapFilling.test_gapfilling_randomforest`)

### Environment

- Updated `poetry` to latest version `1.6.1`
- Updated all packages to their latest versions
- Added new package [yellowbrick](https://www.scikit-yb.org/en/latest/)

## v0.59.0 | 14 Sep 2023

### MeteoScreening from database - update

The class `StepwiseMeteoScreeningDb`, which is used for quality-screening of meteo data
stored in the ETH Grassland Sciences database, has been refactored. It is now using the
previously introduced class `StepwiseOutlierDetection` for outlier
tests. (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb`)

### Removed

The following classes are no longer used and were removed from step-wise outlier detection:

- Removed z-score IQR test, too unreliable (`pkgs.outlierdetection.zscore.zScoreIQR`)
- Similarly, removed seasonal trend decomposition that used z-score IQR test, too
  unreliable (`pkgs.outlierdetection.seasonaltrend.OutlierSTLRIQRZ`)

### Notebooks

- Updated notebook `notebooks/MeteoScreening/StepwiseMeteoScreeningFromDatabase.ipynb`

## v0.58.1 | 13 Sep 2023

### Notebooks

- Added new notebook `notebooks/GapFilling/RandomForestGapFilling.ipynb`
- Added new notebook `notebooks/GapFilling/QuickRandomForestGapFilling.ipynb`
- Added new notebook `notebooks/Workbench/Remove_unneeded_cols.ipynb`

## v0.58.0 | 7 Sep 2023

### Random forest update

The class `RandomForestTS` has been refactored. In essence, it still uses the same
`RandomForestRegressor` as before, but now outputs feature importances additionally
as computed by permutation. More details about permutation importance can be found
in scikit's official documentation
here: [Permutation feature importance](https://scikit-learn.org/stable/modules/permutation_importance.html).

When the model is trained using `.trainmodel()`, a random variable is included as additional
feature. Permutation importances of all features - including the random variable - are then
analyzed. Variables that yield a lower importance score than the random variables are removed
from the dataset and are not used to build the model. Typically, the permutation importance for
the random variable is very close to zero or even negative.

The built-in importance calculation in the `RandomForestRegressor` uses the Gini importance,
an impurity-based feature importance that favors high cardinality features over low cardinality
features. This is not ideal in case of time series data that is combined with categorical data.
Permutation importance is therefore a better indicator whether a variable included in the model
is an important predictor or not.

The class now splits input data into training and testing datasets (holdout set). By
default, the training set comprises 75% of the input data, the testing set 25%. After
the model was trained, it is tested on the testing set. This should give a
better indication of how well the model works on unseen data.

Once `.trainmodel()` is finished, the model is stored internally and can be used to gap-fill
the target variable by calling `.fillgaps()`.

In addition, the class now offers improved output with additional text output and plots
that give more info about model training, testing and application during gap-filling.

`RandomForestTS` has also been streamlined. The option to include timestamp info as features
(e.g., a column describing the season of the respective record) during model building is now
its own function (`.include_timestamp_as_cols()`) and was removed from the class.

### New features

- New class `QuickFillRFTS` that uses `RandomForestTS` in the background to quickly fill time series
  data (`pkgs.gapfilling.randomforest_ts.QuickFillRFTS`)
- New function to include timestamp info as features, e.g. YEAR and DOY (`core.times.times.include_timestamp_as_cols`)
- New function to calculate various model scores, e.g. mean absolute error, R2 and
  more (`core.ml.common.prediction_scores_regr`)
- New function to insert the meteorological season (Northern hemisphere) as variable (`core.times.times.insert_season`).
  For each record in the time series, the seasonal info between spring (March, April, May) and winter (December,
  January, February) is added as integer number (0=spring, summer=1, autumn=2, winter=3).

### Additions

- Added new example dataset, comprising ecosystem fluxes between 1997 and 2022 from the
  [ICOS Class 1 Ecosystem station CH-Dav](https://www.swissfluxnet.ethz.ch/index.php/sites/ch-dav-davos/site-info-ch-dav/).
  This dataset will be used for testing code on long-term time series. The dataset is stored in the `parquet`
  file format, which allows fast loading and saving of datafiles in combination with good compression.
  The simplest way to load the dataset is to use:

```python
from diive.configs.exampledata import load_exampledata_parquet

df = load_exampledata_parquet()
```

### Changes

- Updated README with installation details

### Notebooks

- Updated notebook `notebooks/CalculateVariable/Calculate_VPD_from_TA_and_RH.ipynb`

## v0.57.1 | 23 Aug 2023

### Changes

Updates to class `FormatEddyProFluxnetFileForUpload`, for quickly formatting the EddyPro _fluxnet_
output file to comply with [FLUXNET](https://fluxnet.org/) requirements for uploading data.

### Additions

- **Formatting EddyPro _fluxnet_ files for upload to FLUXNET**: `FormatEddyProFluxnetFileForUpload`

    - Added new method to rename variables from the EddyPro _fluxnet_ file to comply
      with [FLUXNET variable codes](http://www.europe-fluxdata.eu/home/guidelines/how-to-submit-data/variables-codes).
      `._rename_to_variable_codes()`
    - Added new method to remove errneous time periods from dataset `.remove_erroneous_data()`
    - Added new method to remove fluxes from time periods of insufficient signal strength / AGC
      `.remove_low_signal_data()`

### Bugfixes

- Fixed bug: when data points are removed manually using class `ManualRemoval` and the data to be removed
  is a single datetime (e.g., `2005-07-05 23:15:00`) then the removal now also works if the
  provided datetime is not found in the time series. Previously, the class raised the error that
  the provided datetime is not part of the index. (`pkgs.outlierdetection.manualremoval.ManualRemoval`)

### Notebooks

- Updated notebook `notebooks/Formats\FormatEddyProFluxnetFileForUpload.ipynb` to version `3`

## v0.57.0 | 22 Aug 2023

### Changes

- Relaxed conditions a bit when inferring time resolution of time
  series (`core.times.times.timestamp_infer_freq_progressively`, `core.times.times.timestamp_infer_freq_from_timedelta`)

### Additions

- When reading parquet files, the TimestampSanitizer is applied by default to detect e.g. the time resolution
  of the time series. Parquet files do not store info on time resolution like it is stored in pandas dataframes
  (e.g. `30T` for 30MIN time resolution), even if the dataframe containing that info was saved to a parquet file.

### Bugfixes

- Fixed bug where interactive time series plot did not show in Jupyter notebooks (`core.plotting.timeseries.TimeSeries`)
- Fixed bug where certain parts of the flux processing chain could not be used for the sensible heat flux `H`.
  The issue was that `H` is calculated from sonic temperature (`T_SONIC` in EddyPro `_fluxnet_` output files),
  which was not considered in function `pkgs.flux.common.detect_flux_basevar`.
- Fixed bug: interactive plotting in notebooks using `bokeh` did not work. The reason was that the `bokeh` plot
  tools (controls) `ZoomInTool()` and `ZoomOutTool()` do not seem to work anymore. Both tools are now deactivated.

### Notebooks

- Added new notebook for simple (interactive) time series plotting `notebooks/Plotting/TimeSeries.ipynb`
- Updated notebook `notebooks/FluxProcessingChain/FluxProcessingChain.ipynb` to version 3

## v0.55.0 | 18 Aug 2023

This update focuses on the flux processing chain, in particular the creation of the extended
quality flags, the flux storage correction and the creation of the overall quality flag `QCF`.

### New Features

- Added new class `StepwiseOutlierDetection` that can be used for general outlier detection in
  time series data. It is based on the `StepwiseMeteoScreeningDb` class introduced in v0.50.0,
  but aims to be more generally applicable to all sorts of time series data stored in
  files (`pkgs.outlierdetection.stepwiseoutlierdetection.StepwiseOutlierDetection`)
- Added new outlier detection class that identifies outliers based on seasonal-trend decomposition
  and z-score calculations (`pkgs.outlierdetection.seasonaltrend.OutlierSTLRZ`)
- Added new outlier detection class that flags values based on absolute limits that can be defined
  separately for daytime and nighttime (`pkgs.outlierdetection.absolutelimits.AbsoluteLimitsDaytimeNighttime`)
- Added small functions to directly save (`core.io.files.save_as_parquet`) and
  load (`core.io.files.load_parquet`) parquet files. Parquet files offer fast loading and saving in
  combination with good compression. For more information about the Parquet format
  see [here](https://parquet.apache.org/)

### Additions

- **Angle-of-attack**: The angle-of-attack test can now be used during QC flag creation
  (`pkgs.fluxprocessingchain.level2_qualityflags.FluxQualityFlagsLevel2.angle_of_attack_test`)
- Various smaller additions

### Changes

- Renamed class `FluxQualityFlagsLevel2` to `FluxQualityFlagsLevel2EddyPro` because it is directly based
  on the EddyPro output (`pkgs.fluxprocessingchain.level2_qualityflags.FluxQualityFlagsLevel2EddyPro`)
- Renamed class `FluxStorageCorrectionSinglePoint`
  to `FluxStorageCorrectionSinglePointEddyPro` (`pkgs.fluxprocessingchain.level31_storagecorrection.FluxStorageCorrectionSinglePointEddyPro`)
- Refactored creation of flux quality
  flags (`pkgs.fluxprocessingchain.level2_qualityflags.FluxQualityFlagsLevel2EddyPro`)
- **Missing storage correction terms** are now gap-filled using random forest before the storage terms are
  added to the flux. For some records, the calculated flux was available but the storage term was missing, resulting
  in a missing storage-corrected flux (example: 97% of fluxes had storage term available, but for 3% it was missing).
  The gap-filling makes sure that each flux values has a corresponding storage term and thus more values are
  available for further processing. The gap-filling is done solely based on timestamp information, such as DOY
  and hour. (`pkgs.fluxprocessingchain.level31_storagecorrection.FluxStorageCorrectionSinglePoint`)
- The **outlier detection using z-scores for daytime and nighttime data** uses latitude/longitude settings to
  calculate daytime/nighttime via `pkgs.createvar.daynightflag.nighttime_flag_from_latlon`. Before z-score
  calculation, the time resolution of the time series is now checked and assigned automatically.
  (`pkgs.outlierdetection.zscore.zScoreDaytimeNighttime`)
- Removed `pkgs.fluxprocessingchain.level32_outlierremoval.FluxOutlierRemovalLevel32` since flux outlier
  removal is now done in the generally applicable class `StepwiseOutlierDetection` (see new features)
- Various smaller changes and refactorings

### Environment

- Updated `poetry` to newest version `v1.5.1`. The `lock` files have a new format since `v1.3.0`.
- Created new `lock` file for `poetry`.
- Added new package `pyarrow`.
- Added new package `pymannkendall` (see [GitHub](https://pypi.org/project/pymannkendall/)) to analyze
  time series data for trends. Functions of this package are not yet implemented in `diive`.

### Notebooks

- Added new notebook for loading and saving parquet files in `notebooks/Formats/LoadSaveParquetFile.ipynb`
- **Flux processing chain**: Added new notebook for flux post-processing
  in `notebooks/FluxProcessingChain/FluxProcessingChain.ipynb`.

## v0.54.0 | 16 Jul 2023

### New Features

- Identify critical heat days for ecosytem flux NEE (net ecosystem exchange, based on air temperature and VPD
  (`pkgs.flux.criticalheatdays.FluxCriticalHeatDaysP95`)
- Calculate z-aggregates in classes of x and y (`pkgs.analyses.quantilexyaggz.QuantileXYAggZ`)
- Plot heatmap from pivoted dataframe, using x,y,z values (`core.plotting.heatmap_xyz.HeatmapPivotXYZ`)
- Calculate stats for time series and store results in dataframe (`core.dfun.stats.sstats`)
- New helper function to load and merge files of a specific filetype (`core.io.files.loadfiles`)

### Additions

- Added more parameters when formatting EddyPro _fluxnet_ file for FLUXNET
  (`pkgs.formats.fluxnet.FormatEddyProFluxnetFileForUpload`)

### Changes

- Removed left-over code
- Multiple smaller refactorings

### Notebooks

- Added new notebook for calculating VPD in `notebooks/CalculateVariable/Calculate_VPD_from_TA_and_RH.ipynb`
- Added new notebook for calculating time series stats `notebooks/Stats/TimeSeriesStats.ipynb`
- Added new notebook for formatting EddyPro output for upload to
  FLUXNET `notebooks/Formats/FormatEddyProFluxnetFileForUpload.ipynb`

## v0.53.3 | 23 Apr 2023

### Notebooks

- Added new notebooks for reading data files (ICOS BM files)
- Added additional output to other notebooks
- Added new notebook section `Workbench` for practical use cases

### Additions

- New filetype `configs/filetypes/ICOS_H1R_CSVZIP_1MIN.yml`

## v0.53.2 | 23 Apr 2023

### Changes

- Added more output for detecting frequency from timeseries index (`core.times.times.DetectFrequency`)
    - The associated functions have been updated accordingly: `core.times.times.timestamp_infer_freq_from_fullset`,
      `core.times.times.timestamp_infer_freq_progressively`, `core.times.times.timestamp_infer_freq_from_timedelta`
    - Added new notebook (`notebooks/TimeStamps/Detect_time_resolution.ipynb` )
    - Added new unittest (`tests/test_timestamps.py`)

## v0.53.1 | 18 Apr 2023

### Changes

- **GapFinder** now gives by default sorted output, i.e. the output dataframe shows start and
  end date for the largest gaps first (`pkgs.analyses.gapfinder.GapFinder`)

### Notebooks

- Added new notebook for **finding gaps in time series** in `notebooks/Analyses/GapFinder.ipynb`
- Added new notebook for **time functions** in `notebooks/TimeFunctions/times.ipynb`

### Other

- New repository branch `indev` is used as developement branch from now on
- Branch `main` will contain code from the most recent release

## v0.53.0 | 17 Apr 2023

This update focuses on wind direction time series and adds the first example notebooks
to `diive`. From now on, new example notebooks will be added regularly.

### New features

- **Wind direction offset correction**: Compare yearly wind direction histograms to
  reference, detect offset in comparison to reference and correct wind directions
  for offset per year (`pkgs.corrections.winddiroffset.WindDirOffset`)
- **Wind direction aggregation**: Calculate mean etc. of wind direction in
  degrees (`core.funcs.funcs.winddirection_agg_kanda`)

### Notebooks

- Added new notebook for **wind direction offset correction** in `notebooks/Corrections/WindDirectionOffset.ipynb`
- Added new notebok for **reading ICOS BM files** in `notebooks/ReadFiles/Read_data_from_ICOS_BM_files.ipynb`

### Changes

- **Histogram analysis** now accepts pandas Series as input (`pkgs.analyses.histogram.Histogram`)

### Additions

- Added unittests for reading (some) filetypes

## v0.52.7 | 16 Mar 2023

### Additions

- The DataFileReader can now directly read zipped files (`core.io.filereader.DataFileReader`)
- **Interactive time series plot**: (`core.plotting.timeseries.TimeSeries.plot_interactive`)
    - added x- and y-axis to the plots
    - new parameters `width` and `height` allow to control the size of the plot
    - more controls such as undo/redo and zoom in/zoom out buttons were added
- The filetypes defined in `diive/configs/filetypes` now accept the setting `COMPRESSION: "zip"`.
  In essence, this allows to read zipped files directly.
- New filetype `ICOS_H2R_CSVZIP_10S`

### Changes

- Compression in filetypes is now given as `COMPRESSION: "None"` for no compression,
  and `COMPRESSION: "zip"` for zipped CSV files.

## v0.52.6 | 12 Mar 2023

### Additions

- `LocalSD` in `StepwiseMeteoScreeningDb` now accepts the parameter `winsize` to
  define the size of the rolling window (default `None`, in which case the window
  size is calculated automatically as 1/20 of the number of records).
  (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.flag_outliers_localsd_test`)

### Bugfix

- Fixed bug: outlier test `LocalSD` did not consider user input `n_sd`
  (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.flag_outliers_localsd_test`)

## v0.52.4 and v0.52.5 | 10 Mar 2023

### Bugfix

- Fixed bug: during resampling, the info for the tag `data_version` was incorrectly
  stored in tag `freq`. (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.resample`)

## v0.52.3 | 10 Mar 2023

## Additions

- Added plotting library `bokeh` to dependencies

### Changes

- When combining data of different time resolutions, the data are now combined using
  `.combine_first()` instead of `.concat()` to avoid duplicates during merging. This
  should work reliably because data of the highest resolution are available first, and then
  lower resolution upsampled (backfilled) data are added, filling gaps in the high
  resolution data. Because gaps are filled, overlaps between the two resolutions are avoided.
  With `.concat()`, gaps were not filled, but timestamps were simply added as new records,
  and thus duplicates in the timestamp occurred.
  (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb._harmonize_timeresolution`)
- Updated dependencies to newest possible versions

## v0.52.2 | 9 Mar 2023

### Changes

- Removed the packages `jupyterlab` and `jupyter-bokeh` from dependencies, because
  the latter caused issues when trying to install `diive` in a `conda` environment
  on a shared machine. Both dependencies are still listed in the `pyproject.toml`
  file as `dev` dependencies. It makes sense to keep both packages separate from
  `diive` because they are specifically for `jupyter` notebooks and not strictly
  related to `diive` functionality.

## v0.52.1 | 7 Mar 2023

### Additions

- In `StepwiseMeteoScreeningDb` the current cleaned timeseries can now be
  plotted with `showplot_current_cleaned`.
- Timeseries can now be plotted using the `bokeh` library. This plot are interactive
  and can be directly used in jupyter notebooks. (`core.plotting.timeseries.TimeSeries`)
- Added new plotting package `jupyter_bokeh` for interactive plotting in Jupyter lab.
- Added new plotting package `seaborn`.

### Bugfixes

- `StepwiseMeteoScreeningDb` now works on a copy of the input data to avoid
  unintended data overwrite of input.

## v0.52.0 | 6 Mar 2023

### New Features

- **Data formats**: Added new package `diive/pkgs/formats` that assists in converting
  data outputs to formats required e.g. for data sharing with FLUXNET.
    - Convert the EddyPro `_fluxnet_` output file to the FLUXNET data format for
      data upload (data sharing). (`pkgs.formats.fluxnet.ConvertEddyProFluxnetFileForUpload`)
- **Insert timestamp column**: Insert timestamp column that shows the START, END
  or MIDDLE time of the averaging interval (`core.times.times.insert_timestamp`)
- **Manual removal of data points**: Flag manually defined data points as outliers.
  (`pkgs.outlierdetection.manualremoval.ManualRemoval`)

### Additions

Added additional outlier detection algorithms
to `StepwiseMeteoScreeningDb` (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb`):

- Added local outlier factor test, across all data
  (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.flag_outliers_lof_test`)
- Added local outlier factor test, separately for daytime and nighttime
  (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.flag_outliers_lof_dtnt_test`)

## v0.51.0 | 3 Mar 2023

### Random uncertainty

- Implemented random flux uncertainty calculation, based on Holliner and Richardson (2005)
  and Pastorello et al. (2020). Calculations also include a first estimate of the error
  propagation when summing up flux values to annual sums. See end of CHANGELOG for links to references.
  (`pkgs.flux.uncertainty.RandomUncertaintyPAS20`)

### Additions

- Added example data in `diive/configs/exampledata`, including functions to load the data.

### Changes

- In `core.io.filereader`, the following classes now also accept `output_middle_timestamp`
  (boolean with default `True`) as parameter: `MultiDataFileReader`, `ReadFileType`,`DataFileReader`.
  This allows to keep the original timestamp of the data.
- Some minor plotting adjustments

## v0.50.0 | 12 Feb 2023

### StepwiseMeteoScreeningDb

**Stepwise quality-screening of meteorological data, directly from the database**

In this update, the stepwise meteoscreening directly from the database introduced in the
previous update was further refined and extended, with additional outlier tests and corrections
implemented. The stepwise meteoscreening allows to perform step-by-step quality tests on
meteorological. A preview plot after running a test is shown and the user can decide if
results are satisfactory or if the same test with different parameters should be re-run.
Once results are satisfactory, the respective test flag is added to the data. After running
the desired tests, an overall flag `QCF` is calculated from all individual tests.

In addition to the creation of quality flags, the stepwise screening allows to correct
data for common issues. For example, short-wave radiation sensors often measure negative
values during the night. These negative values are useful because they give info about
the accuracy and precision of the sensor. In this case, values during the night should
be zero. Instead of cutting off negative values, `diive` detects the nighttime offset
for each day and then calculates a correction slope between individual days. This way,
the daytime values are also corrected.

After quality-screening and corrections, data are resampled to 30MIN time resolution.

At the moment, the stepwise meteoscreening works for data downloaded from the `InfluxDB`
database. The screening respects the database format (including tags) and prepares
the screened, corrected and resampled data for direct database upload.

Due to its modular approach, the stepwise screening can be easily adjusted
to work with any type of data files. This adjustment will be done in one of the next
updates.

### Changes

- Renamed class `MetScrDbMeasurementVars`
  to `StepwiseMeteoScreeningDb` (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb`)

### Additions

- **Stepwise MeteoScreening**:
  Added access to multiple methods for easy stepwise execution:
    - Added local SD outlier test (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.flag_outliers_localsd_test`)
    - Added absolute limits outlier test (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.flag_outliers_abslim_test`)
    - Added correction to remove radiation zero
      offset (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.correction_remove_radiation_zero_offset`)
    - Added correction to remove relative humidity
      offset (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.correction_remove_relativehumidity_offset`)
    - Added correction to set values above a threshold to
      threshold (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.correction_setto_max_threshold`)
    - Added correction to set values below a threshold to
      threshold (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.correction_setto_min_threshold`)
    - Added comparison plot before/after QC and
      corrections (`pkgs.qaqc.meteoscreening.StepwiseMeteoScreeningDb.showplot_resampled`)

## v0.49.0 | 10 Feb 2023

### New Features

- **Stepwise MeteoScreening**: (`pkgs.qaqc.meteoscreening.MetScrDbMeasurementVars`)
    - **Helper class to screen time series of meteo variables directly from the
      database**. The class is optimized to work in Jupyter notebooks. Various outlier
      detection methods can be called on-demand. Outlier results are displayed and
      the user can accept the results and proceed, or repeat the step with adjusted
      method parameters. An unlimited amount of tests can be chained together. At
      the end of the screening, an overall flag is calculated from ALL single flags.
      The overall flag is then used to filter the time series.
    - **Variables**: The class allows the simultaneous quality-screening of multiple
      variables from one single measurement, e.g., multiple air temperature variables.
    - **Resampling**:Filtered time series are resampled to 30MIN time resolution.
    - **Database tags**: Is optimized to work with the InfluxDB format of the ETH
      Grassland Sciences Group. The class can handle database tags and updates tags
      after data screening and resampling.
    - **Handling different time resolutions**: One challenging aspect of the screening
      were the different time resolutions of the raw data. In some cases, the time
      resolution changed from e.g. 10MIN for older data to 1MIN for newer date. In
      cases of different time resolution, the lower resolution is upsampled to the
      higher resolution, the emerging gaps are back-filled with available data.
      Back-filling is used because the timestamp in the database always is TIMESTAMP_END,
      i.e., it gives the *end* of the averaging interval. The advantage of upsampling
      is that all outlier detection routines can be applied to the whole dataset.
      Since data are resampled to 30MIN after screening and since the TIMESTAMP_END
      is respected, the upsampling itself has no impact on resulting aggregates.

### Changes

- Generating the plot NEP penalty vs hours above threshold now requires a
  minimum of 2 bootstrap runs to calculate prediction intervals
  (`pkgs.flux.nep_penalty.NEPpenalty.plot_critical_hours`)

### Bugfixes

- Fixed bug in `BinFitter`, the parameter to set the number of predictions is now correctly
  named `n_predictions`. Similar `n_bins_x`.
- Fixed typos in functions `insert_aggregated_in_hires`, `SortingBinsMethod`, `FindOptimumRange`
  and `pkgs.analyses.optimumrange.FindOptimumRange._values_in_optimum_range` and others.
- Other typos

## v0.48.0 | 1 Feb 2023

### New Features

- **USTAR threshold**: (`pkgs.flux.ustarthreshold.UstarThresholdConstantScenarios`)
    - Calculates how many records of e.g. a flux variable are still available after the application
      of different USTAR thresholds. In essence, it gives an overview of the sensitivity of the
      variable to different thresholds.
- **Outlier detection, LOF across all data**: (`pkgs.outlierdetection.lof.LocalOutlierFactorAllData`)
    - Calculation of the local outlier factor across all data, i.e., no differentiation between
      daytime and nighttime data.
- **Outlier detection, increments**: (`pkgs.outlierdetection.incremental.zScoreIncremental`)
    - Based on the absolute change of on record in comparison to the previous record. These
      differences are stored as timeseries, the z-score is calculated and outliers are removed
      based on the observed differences. Works well with data that do not have a diel cycle,
      e.g. soil water content.

![DIIVE](images/fluxUstarthreshold_UstarThresholdConstantScenarios_diive_v0.48.0.png)

## v0.47.0 | 28 Jan 2023

### New Features

- **Outlier detection**: LOF, local outlier factor**: (`pkgs.outlierdetection.lof.LocalOutlierFactorDaytimeNighttime`)
    - Identify outliers based on the local outlier factor, done separately for
      daytime and nighttime data
- **Multiple z-score outlier detections**:
    - Simple outlier detection based on the z-score of observations, calculated from
      mean and std from the complete timeseries. (`pkgs.outlierdetection.zscore.zScore`)
    - z-score outlier detection separately for daytime and nighttime
      data (`pkgs.outlierdetection.zscore.zScoreDaytimeNighttime`)
    - Identify outliers based on the z-score of the interquartile range data (`pkgs.outlierdetection.zscore.zScoreIQR`)
- **Outlier detection**: (`pkgs.fluxprocessingchain.level32_outlierremoval.OutlierRemovalLevel32`):
    - Class that allows to apply multiple methods for outlier detection during as part of the flux processing chain

### Changes

- **Flux Processing Chain**:
    - Worked on making the chain more accessible to users. The purpose of the modules in
      `pkgs/fluxprocessingchain` is to expose functionality to the user, i.e., they make
      functionality needed in the chain accessible to the user. This should be as easy as possible
      and this update further simplified this access. At the moment there are three modules in
      `pkgs/fluxprocessingchain/`: `level2_qualityflags.py`, `level31_storagecorrection.py` and
      `level32_outlierremoval.py`. An example for the chain is given in `fluxprocessingchain.py`.
- **QCF flag**: (`pkgs.qaqc.qcf.FlagQCF`)
    - Refactored code: the creation of overall quality flags `QCF` is now done using the same
      code for flux and meteo data. The general logic of the `QCF` calculation is that results
      from multiple quality checks that are stored as flags in the data are combined into
      one single quality flag.
- **Outlier Removal using STL**:
    - Module was renamed to `pkgs.outlierdetection.seasonaltrend.OutlierSTLRIQRZ`. It is not the
      most convenient name, I know, but it stands for **S**easonal **T**rend decomposition using
      **L**OESS, based on **R**esidual analysis of the **I**nter**Q**uartile **R**ange using **Z**-scores
- **Search files** can now search in subfolders of multiple base folders (`core.io.filereader.search_files`)

## v0.46.0 | 23 Jan 2023

### New Features

- **Outlier Removal using STL**: (`pkgs.outlierdetection.seasonaltrend.OutlierSTLIQR`)
    - Implemented first code to remove outliers using seasonal-srend decomposition using LOESS.
      This method divides a time series into seasonal, trend and residual components. `diive`
      uses the residuals to detect outliers based on z-score calculations.
- **Overall quality flag for meteo data**: (`pkgs.qaqc.qcf.MeteoQCF`)
    - Combines the results from multiple flags into one single flag
    - Very similar to the calculation of the flux QCF flag

### Changes

- **MeteoScreening**: (`diive/pkgs/qaqc/meteoscreening.py`)
    - Refactored most of the code relating to the quality-screening of meteo data
    - Implemented the calculation of the overall quality flag QCF
    - Two overview figures are now created at the end on the screening
    - Flags for tests used during screening are now created using a base class (`core.base.flagbase.FlagBase`)
- **Flux Processing Chain**: All modules relating to the Swiss FluxNet flux processing
  chain are now collected in the dedicated package `fluxprocessingchain`. Relevant
  modules were moved to this package, some renamed:
    - `pkgs.fluxprocessingchain.level2_qualityflags.QualityFlagsLevel2`
    - `pkgs.fluxprocessingchain.level31_storagecorrection.StorageCorrectionSinglePoint`
    - `pkgs.fluxprocessingchain.qcf.QCF`
- **Reading YAML files**: (`core.io.filereader.ConfigFileReader`)
    - Only filetype configuration files are validated, i.e. checked if they follow the
      expected file structure. However, there can be other YAML files, such as the file
      `pipes_meteo.yaml` that defines the QA/QC steps for each meteo variable. For the
      moment, only the filetype files are validated and the validation is skipped for
      the pipes file.
- Refactored calculation of nighttime flag from sun altitude: code is now vectorized
  and runs - unsurprisingly - much faster (`pkgs.createvar.nighttime_latlon.nighttime_flag_from_latlon`)
- Some smaller changes relating to text output to the console

## v0.45.0 | 13 Jan 2023

### New Features

- **Flux storage correction**: (`pkgs.flux.storage.StorageCorrectionSinglePoint`)
    - Calculate storage-corrected fluxes
    - Creates Level-3.1 in the flux processing chain
- **Overall quality flag**: (`pkgs.qaqc.qcf.QCF`)
    - Calculate overall quality flag from multiple individual flags

### Changes

- **Flux quality-control**: (`pkgs.qaqc.fluxes.QualityFlagsLevel2`)
    - Flags now have the string `_L2_` in their name to identify them as
      flags created during Level-2 calculations in the Swiss FluxNet flux
      processing chain.
    - All flags can now be returned to the main data
- Renamed `pkgs.qaqc.fluxes.FluxQualityControlFlag` to `pkgs.qaqc.fluxes.QualityFlagsLevel2`

## v0.44.1 | 11 Jan 2023

### Changes

- **Flux quality-control**: (`pkgs.qaqc.fluxes.FluxQualityControlFlag`)
    - Added heatmap plots for before/after QC comparison
    - Improved code for calculation of overall flag `QCF`
    - Improved console output

## v0.44.0 | 9 Jan 2023

### New Features

- **Flux quality-control**: (`pkgs.qaqc.fluxes.FluxQualityControlFlag`)
    - First implementation of quality control of ecosystem fluxes. Generates one
      overall flag (`QCF`=quality control flag) from multiple quality test results
      in EddyPro's `fluxnet` output file. The resulting `QCF` is Level-2 in the
      Swiss FluxNet processing chain,
      described [here](https://www.swissfluxnet.ethz.ch/index.php/data/ecosystem-fluxes/flux-processing-chain/).
      `QCF` is mostly based on the ICOS methodology, described
      by [Sabbatini et al. (2018)](https://doi.org/10.1515/intag-2017-0043).
- **Histogram**: (`pkgs.analyses.histogram.Histogram`)
    - Calculates histogram from time series, identifies peak distribution
- **Percentiles**: (`pkgs.analyses.quantiles.percentiles`)
    - Calculates percentiles (0-100) for a time series
- **Scatter**: Implemented first version of `core.plotting.scatter.Scatter`, which will
  be used for scatter plots in the future

### Changes

- **Critical days**: (`pkgs.flux.criticaldays.CriticalDays`)
    - Renamed Variables, now using Dcrit (instead of CRD) and nDcrit (instead of nCRD)
- **NEP Penalty**: (`pkgs.flux.nep_penalty.NEPpenalty`)
    - Code was refactored to work with NEP (net ecosystem productivity) instead of NEE
      (net ecosystem exchange)
    - CO2 penalty was renamed to the more descriptive NEP penalty
- **Sanitize column names**: implemented in `core.io.filereader.ColumnNamesSanitizer`
  Column names are now checked for duplicates. Found duplicates are renamed by adding a
  suffix to the column name. Example: `co2_mean` and `co2_mean` are renamed to
  `co2_mean.1` and `co2_mean.2`. This check is now implemented during the reading of
  the data file in `core.io.filereader.DataFileReader`.
- **Configuration files**: When reading filetype configuration files in `core.io.filereader.ConfigFileReader`,
  the resulting dictionary that contains all configurations is now validated. The validation makes
  sure the parameters for `.read_csv()` are in the proper format.
- Updated all dependencies to their newest (possible) version

### Additions

- Added support for filetype `EDDYPRO_FLUXNET_30MIN` (`configs/filetypes/EDDYPRO_FLUXNET_30MIN.yml`)

## v0.43.0 | 8 Dec 2022

### New Features

- **Frequency groups detection**: Data in long-term datasets are often characterized by changing time
  resolutions at which data were recorded. `core.times.times.detect_freq_groups` detects changing
  time resolutions in datasets and adds a group identifier in a new column that gives info about the
  detected time resolution in seconds, e.g., `600` for 10MIN data records. This info allows to
  address and process the different time resolutions separately during later processing, which is
  needed e.g. during data quality-screening and resampling.
- **Outlier removal using z-score**: First version of `pkgs.outlierdetection.zscore.zscoreiqr`
  Removes outliers based on the z-score of interquartile range data. Data are divided
  into 8 groups based on quantiles. The z-score is calculated for each data point
  in the respective group and based on the mean and SD of the respective group.
  The z-score threshold to identify outlier data is calculated as the max of
  z-scores found in IQR data multiplied by *factor*. z-scores above the threshold
  are marked as outliers.
- **Outlier removal using local standard deviation**: First version of `pkgs.outlierdetection.local3sd.localsd`
  Calculates mean and SD in a rolling window and marks data points outside a specified range.

### Additions

- **MeteoScreening**: Added the new parameter `resampling_aggregation` in the meteoscreening setting
  `diive/pkgs/qaqc/pipes_meteo.yaml`. For example, `TA` needs `mean`, `PRECIP` needs `sum`.

### Changes

- **MeteoScreening**: `pkgs.qaqc.meteoscreening.MeteoScreeningFromDatabaseSingleVar`
  Refactored the merging of quality-controlled 30MIN data when more than one raw data time
  resolution is involved.
- **Resampling**: `core.times.resampling.resample_series_to_30MIN`
  The minimum required values for resampling is `1`. However, this is only relevant for
  lower resolution data e.g. 10MIN and 30MIN, because for higher resolutions the calculated value
  for minimum required values yields values > 1 anyway. In addition, if data are already in
  30MIN resolution, they are still going through the resampling processing although it would not
  be necessary, because the processing includes other steps relevant to all data resolutions, such
  as the change of the timestamp from TIMESTAMP_MIDDLE to TIMESTAMP_END.

### Bugs

- Removed display bug when showing data after high-res meteoscreening in heatmap. Plot showed
  original instead of meteoscreened data

## v0.42.0 | 27 Nov 2022

### New Features

- **Decoupling**: Added first version of decoupling code (`pkgs.analyses.decoupling.SortingBinsMethod`).
  This allows the investigation of binned aggregates of a variable `z` in binned classes of
  `x` and `y`. For example: show mean GPP (`y`) in 5 classes of VPD (`x`), separate for
  10 classes of air temperature (`z`).

![DIIVE](images/analysesDecoupling_sortingBinsMethod_diive_v0.42.0.png)

- **Time series plot**: `core.plotting.timeseries.TimeSeries` plots a simple time series. This will
  be the default method to plot time series.

### Changes

- **Critical days**: Several changes in `pkgs.flux.criticaldays.CriticalDays`:

    - By default, daily aggregates are now calculated from 00:00 to 00:00 (before it was
      7:00 to 07:00).
    - Added parameters for specifying the labels for the x- and y-axis in output figure
    - Added parameter for setting dpi of output figure
    - Some smaller adjustments
    - `pkgs.flux.co2penalty.CO2Penalty.plot_critical_hours`: 95% predicion bands are now
      smoothed (rolling mean)

- **CO2 penalty**: (since v0.44.0 renamed to NEP penalty)

    - Some code refactoring in `pkgs.flux.co2penalty.CO2Penalty`, e.g. relating to plot appearances

## v0.41.0 | 5 Oct 2022

### BinFitterBTS

- `pkgs.fits.binfitter.BinFitterBTS` fits a quadratic or linear equation to data.
- This is a refactored version of the previous `BinFitter` to allow more options.
- Implemented `pkgs.fits.binfitter.PlotBinFitterBTS` for plotting `BinFitterBTS` results
- `PlotBinFitterBTS` now allows plotting of confidence intervals for the upper and
  lower prediction bands
- The updated `BinFitterBTS` is now implemented in `pkgs.flux.criticaldays.CriticalDays`

#### Example of updated `BinFitterBTS` as used in `CriticalDays`

It is now possible to show confidence intervals for the upper and lower prediction bands.  
![DIIVE](images/fluxCriticalDaysWithUpdatedBinFitterBTS_diive_v0.41.0.png)

### Other

- `core.plotting.heatmap_datetime.HeatmapDateTime` now accepts `figsize`
- When reading a file using `core.io.filereader.ReadFileType`, the index column is now
  parsed to a temporarily named column. After reading the file data, the temporary column
  name is renamed to the correct name. This was implemented to avoid duplicate issues
  regarding the index column when parsing the file, because a data column with the same
  name as the index column might be in the dataset.

### Bugfixes

- Fixed bug in `pkgs.gapfilling.randomforest_ts.RandomForestTS`: fallback option for
  gap-filling was never used and some gaps would remain in the time series.

## v0.40.0 | 23 Sep 2022

### CO2 Penalty

- New analysis: `pkgs.flux.co2penalty.CO2Penalty` calculates the CO2 penalty as
  the difference between the observed co2 flux and the potential co2 flux modelled
  from less extreme environmental conditions.

![DIIVE](images/fluxCO2penalty_cumulative_diive_v0.40.0.png)

![DIIVE](images/fluxCO2penalty_penaltyPerYear_diive_v0.40.0.png)

![DIIVE](images/fluxCO2penalty_dielCycles_diive_v0.40.0.png)

### VPD Calculation

- New calculation: `pkgs.createvar.vpd.calc_vpd_from_ta_rh` calculates vapor pressure
  deficit (VPD) from air temperature and relative humidity

### Fixes

- Fixed: `core.plotting.cumulative.CumulativeYear` now shows zero line if needed
- Fixed: `core.plotting.cumulative.CumulativeYear` now shows proper axis labels

## v0.39.0 | 4 Sep 2022

### Critical Days

- New analysis: `pkgs.flux.criticaldays.CriticalDays` detects days in y that are
  above a detected x threshold. At the moment, this is implemented to work with
  half-hourly flux data as input and was tested with VPD (x) and NEE (y). In the
  example below critical days are defined as the VPD daily max value where the daily
  sum of NEE (in g CO2 m-2 d-1) becomes positive (i.e., emission of CO2 from the
  ecosystem to the atmosphere).
  ![DIIVE](images/fluxCriticalDays_diive_v0.39.0.png)

## v0.38.0 | 3 Sep 2022

### Optimum Range Detection

- New analysis: `pkgs.analyses.optimumrange.FindOptimumRange` finds the optimum for a
  variable in binned other variable. This is useful for e.g. detecting the VPD
  range where CO2 uptake was highest (=most negative).  
  ![DIIVE](images/analysesOptimumRange_diive_v0.38.0.png)

## v0.37.0 | 2 Sep 2022

### Cumulative and Anomaly Plots

- New plot: `core.plotting.cumulative.CumulativeYear` plots cumulative sums per year  
  ![DIIVE](images/plotCumulativeYear_diive_v0.37.0.png)
- New plot: `core.plotting.bar.LongtermAnomaliesYear` plots yearly anomalies in relation to a reference period  
  ![DIIVE](images/plotBarLongtermAnomaliesYear_diive_v0.37.0.png)
- Refactored various code bits for plotting

## v0.36.0 | 27 Aug 2022

### Random Forest Update

- Refactored code for `pkgs/gapfilling/randomforest_ts.py`
    - Implemented lagged variants of variables
    - Implemented long-term gap-filling, where the model to gap-fill a specific year is built from the
      respective year and its neighboring years
    - Implemented feature reduction using sklearn's RFECV
    - Implemented TimeSeriesSplit used as the cross-validation splitting strategy during feature reduction
- Implemented `TimestampSanitizer` also when reading from file with `core.io.filereader.DataFileReader`
- Removed old code in `.core.dfun.files` and moved files logistics to `.core.io.files` instead
- Implemented saving and loading Python `pickles` in `.core.io.files`

## v0.35.0 | 19 Aug 2022

### Meteoscreening PA, RH

- Added function `pkgs.corrections.offsetcorrection.remove_relativehumidity_offset` to correct
  humidity measurements for values > 100%

### Other

- Added first code for outlier detection via seasonal trends in `pkgs/outlierdetection/seasonaltrend.py`
- Prepared `pkgs/analyses/optimumrange.py` for future updates

## v0.34.0 | 29 Jul 2022

### MeteoScreening Radiation

#### MeteoScreening

- Implemented corrections and quality screening for radiation data in `pkgs.qaqc.meteoscreening`

#### Corrections

Additions to `pkgs.corrections`:

- Added function `.offsetcorrection.remove_radiation_zero_offset` to correct radiation
  data for nighttime offsets
- Added function `.setto_threshold.setto_threshold` to set values above or below a
  specfied threshold value to the threshold.

#### Plotting

- Added function `core.plotting.plotfuncs.quickplot` for quickly plotting pandas
  Series and DataFrame data

#### Resampling

- Implemented `TimeSanitizer` in `core.times.resampling.resample_series_to_30MIN`

#### Other

- Added decorator class `core.utils.prints.ConsoleOutputDecorator`, a wrapper to
  execute functions with additional info that is output to the console.

## v0.33.0 | 26 Jul 2022

### MeteoScreening Preparations

- Added new class `core.times.times.TimestampSanitizer`
    - Class that handles timestamp checks and fixes, such as the creation of a continuous
      timestamp without date gaps.
- Added `pkgs.createvar.nighttime_latlon.nighttime_flag_from_latlon`
    - Function for the calculation of a nighttime flag (1=nighttime) from latitude and
      longitude coordinates of a specific location.
- Added `core.plotting.heatmap_datetime.HeatmapDateTime`
    - Class to generate a heatmap plot from timeseries data.

## v0.32.0 | 22 Jul 2022

### MeteoScreening Air Temperature

MeteoScreening uses a general settings file `pipes_meteo.yaml` that contains info how
specific `measurements` should be screened. Such `measurements` group similar variables
together, e.g. different air temperatures are measurement `TA`.   
Additions to module `pkgs.qaqc.meteoscreening`:

- Added class `ScreenVar`
    - Performs quality screening of air temperature `TA`.
    - As first check, I implemented outlier detection via the newly added package `ThymeBoost`,
      along with checks for absolute limits.
    - Screening applies the checks defined in the file `pipes_meteo.yaml` for the respective
      `measurement`, e.g. `TA` for air temperature.
    - The screening outputs a separate dataframe that contains `QCF` flags for each check.
    - The checks do not change the original time series. Instead, only the flags are generated.
    - Screening routines for more variables will be added over the next updates.
- Added class `MeteoScreeningFromDatabaseSingleVar`
    - Performs quality screening *and* resampling to 30MIN of variables downloaded from the database.
    - It uses the `detailed` data when downloading data from the database using `dbc-influxdb`.
    - The `detailed` data contains the measurement of the variable, along with multiple tags that
      describe the data. The tags are needed for storage in the database.
    - After quality screening of the original high-resolution data, flagged values are removed and
      then data are resampled.
    - It also handles the issue that data downloaded for a specific variable can have different time
      resolution over the years, although I still need to test this.
    - After screening and resampling, data are in a format that can be directly uploaded to the
      database using `dbc-influxdb`.
- Added class `MeteoScreeningFromDatabaseMultipleVars`
    - Wrapper where multiple variables can be screened in one run.
    - This should also work in combination of different `measurements`. For example, screening
      radiation and temperature data in one run.

### Outlier Detection

Additions to `pkgs.outlierdetection`:

- Added module `thymeboost`
- Added module `absolute_limits`

[//]: # (- optimum range)

[//]: # (- `diive.core.times` `DetectFrequency` )

[//]: # (- `diive.core.times`: `resampling` module )

[//]: # (- New package in env: `ThymeBoost` [GitHub]&#40;https://github.com/tblume1992/ThymeBoost/tree/main/ThymeBoost&#41; )

## v0.31.0 | 4 Apr 2022

### Carbon cost

#### **GENERAL**

- This version introduces the code for calculating carbon cost and critical heat days.

#### **NEW PACKAGES**

- Added new package for flux-specific calculations: `diive.pkgs.flux`

#### **NEW MODULES**

- Added new module for calculating carbon cost: `diive.pkgs.flux.carboncost`
- Added new module for calculating critical heat days: `diive.pkgs.flux.criticalheatdays`

#### **CHANGES & ADDITIONS**

- None

#### **BUGFIXES**

- None

## v0.30.0 | 15 Feb 2022

### Starting diive library

#### **GENERAL**

The `diive` library contains packages and modules that aim to facilitate working
with time series data, in particular ecosystem data.

Previous versions of `diive` included a GUI. The GUI component will from now on
be developed separately as `diive-gui`, which makes use of the `diive` library.

Previous versions of `diive` (up to v0.22.0) can be found in the separate repo
[diive-legacy](https://gitlab.ethz.ch/diive/diive-legacy).

This initial version of the `diive` library contains several first versions of
packages that will be extended with the next versions.

Notable introduction in this version is the package `echires` for working with
high-resolution eddy covariance data. This package contains the module `fluxdetectionlimit`,
which allows the calculation of the flux detection limit following Langford et al. (2015).

#### **NEW PACKAGES**

- Added `common`: Common functionality, e.g. reading data files
- Added `pkgs > analyses`: General analyses
- Added `pkgs > corrections`: Calculate corrections for existing variables
- Added `pkgs > createflag`: Create flag variables, e.g. for quality checks
- Added `pkgs > createvar`: Calculate new variables, e.g. potential radiation
- Added `pkgs > echires`: Calculations for eddy covariance high-resolution data, e.g. 20Hz data
- Added `pkgs > gapfilling`: Gap-filling routines
- Added `pkgs > outlierdetection`: Outlier detection
- Added `pkgs > qaqc`: Quality screening for timeseries variables

#### **NEW MODULES**

- Added `optimumrange` in `pkgs > analyses`
- Added `gapfinder` in `pkgs > analyses`
- Added `offsetcorrection` in `pkgs > corrections`
- Added `setto_threshold` in `pkgs > corrections`
- Added `outsiderange` in `pkgs > createflag`
- Added `potentialradiation` in `pkgs > createvar`
- Added `fluxdetectionlimit` in `pkgs > echires`
- Added `interpolate` in `pkgs > gapfilling`
- Added `hampel` in `pkgs > outlierdetection`
- Added `meteoscreening` in `pkgs > qaqc`

#### **CHANGES & ADDITIONS**

- None

#### **BUGFIXES**

- None

#### **REFERENCES**

Langford, B., Acton, W., Ammann, C., Valach, A., & Nemitz, E. (2015). Eddy-covariance data with low signal-to-noise
ratio: Time-lag determination, uncertainties and limit of detection. Atmospheric Measurement Techniques, 8(10),
4197–4213. https://doi.org/10.5194/amt-8-4197-2015

# References

- Hollinger, D. Y., & Richardson, A. D. (2005). Uncertainty in eddy covariance measurements
  and its application to physiological models. Tree Physiology, 25(7),
  873–885. https://doi.org/10.1093/treephys/25.7.873
- Pastorello, G. et al. (2020). The FLUXNET2015 dataset and the ONEFlux processing pipeline
  for eddy covariance data. 27. https://doi.org/10.1038/s41597-020-0534-3

