# TODO TimeSeriesSplit like in https://www.youtube.com/watch?v=z3ZnOW-S550
# TODO generalization bias
# TODO SHAP values
# https://pypi.org/project/shap/
# https://mljar.com/blog/feature-importance-in-random-forest/

"""
=========================================
RANDOM FOREST GAP-FILLING FOR TIME SERIES
randomforest_ts
=========================================

This module is part of the diive library:
https://gitlab.ethz.ch/diive/diive

    - Example notebook available in:
        notebooks/GapFilling/RandomForestGapFilling.ipynb

Kudos, optimization of hyper-parameters, grid search
- https://scikit-learn.org/stable/modules/grid_search.html
- https://www.kaggle.com/code/carloscliment/random-forest-regressor-and-gridsearch

"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
from pandas import DataFrame
from sklearn.ensemble import RandomForestRegressor  # Import the model we are using
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split

import diive.core.dfun.frames as fr
from diive.core.ml.common import prediction_scores_regr, plot_prediction_residuals_error_regr
from diive.core.times.times import TimestampSanitizer
from diive.core.times.times import include_timestamp_as_cols

pd.set_option('display.max_rows', 50)
pd.set_option('display.max_columns', 12)
pd.set_option('display.width', 1000)


class XGBoostTS:

    def __init__(
            self,
            input_df: DataFrame,
            target_col: str or tuple,
            verbose: int = 0,
            perm_n_repeats: int = 10,
            test_size: float = 0.25,
            features_lag: list = None,
            features_lagmax: int = None,
            include_timestamp_as_features: bool = False,
            add_continuous_record_number: bool = False,
            sanitize_timestamp: bool = False,
            **kwargs
    ):
        """
        Gap-fill timeseries with predictions from random forest model

        Args:
            input_df:
                Contains timeseries of 1 target column and 1+ feature columns.

            target_col:
                Column name of variable in *input_df* that will be gap-filled.

            perm_n_repeats:
                Number of repeats for calculating permutation feature importance.

            test_size:
                Proportion of the dataset to include in the test split,
                between 0.0 and 1.0.

            features_lag:
                List of integers (number of records), includes lagged variants of predictors.
                If features_lag=None, no lagged variants are added.
                Example:
                    - features_lag=[-2, +2] includes variants that are lagged by -2, -1, +1 and
                    +2 records in the dataset, for each feature already present in the data.
                     For a variable named *TA*, this created the following output:
                    TA    = [  5,   6,   7, 8  ]
                    TA-2  = [NaN, NaN,   5, 6  ]
                    TA-1  = [NaN,   5,   6, 7  ]  --> each TA record is paired with the preceding record TA-1
                    TA+1  = [  6,   7,   8, NaN]  --> each TA record is paired with the next record TA+1
                    TA+2  = [  7,   8, NaN, NaN]

            include_timestamp_as_features:
                Include timestamp info as integer data: year, season, month, week, doy, hour

            add_continuous_record_number:
                Add continuous record number as new column

            sanitize_timestamp:
                Validate and prepare timestamps for further processing

        Attributes:
            gapfilled_df
            - .PREDICTIONS_FULLMODEL uses the output from the full RF model where
              all features where available.
            - .PREDICTIONS_FALLBACK uses the output from the fallback RF model, which
              was trained on the combined observed + .PREDICTIONS_FULLMODEL data, using
              only the timestamp info as features.
        """

        # Args
        self.model_df = input_df.copy()
        self.target_col = target_col
        self.kwargs = kwargs
        self.perm_n_repeats = perm_n_repeats
        self.test_size = test_size
        self.features_lag = features_lag
        self.features_lagmax = features_lagmax
        self.verbose = verbose

        self._check_n_cols()

        if self.features_lag:
            self.model_df = self._lag_features()

        if include_timestamp_as_features:
            self.model_df = include_timestamp_as_cols(df=self.model_df, txt="")

        if add_continuous_record_number:
            self.model_df = fr.add_continuous_record_number(df=self.model_df)

        if sanitize_timestamp:
            verbose = True if verbose > 0 else False
            tss = TimestampSanitizer(data=self.model_df, output_middle_timestamp=True, verbose=verbose)
            self.model_df = tss.get()

        self.random_col = None

        # Attributes
        self._gapfilling_df = None  # Will contain gapfilled target and auxiliary variables
        self._model = None
        self._feature_importances = dict()
        self._feature_importances_traintest = dict()
        self._feature_importances_reduction = dict()
        self._scores = dict()
        self._scores_test = dict()
        self._accepted_features = []
        self._rejected_features = []

    def get_gapfilled_target(self):
        """Gap-filled target time series"""
        return self.gapfilling_df_[self.target_gapfilled_col]

    def get_flag(self):
        """Gap-filling flag, where 0=observed, 1=gap-filled, 2=gap-filled with fallback"""
        return self.gapfilling_df_[self.target_gapfilled_flag_col]

    @property
    def model_(self) -> RandomForestRegressor:
        """Return model, trained on test data"""
        if not self._model:
            raise Exception(f'Not available: model.')
        return self._model

    @property
    def feature_importances_(self) -> DataFrame:
        """Return feature importance for model used in gap-filling"""
        if not isinstance(self._feature_importances, DataFrame):
            raise Exception(f'Not available: feature importances for gap-filling.')
        return self._feature_importances

    @property
    def feature_importances_traintest_(self) -> DataFrame:
        """Return feature importance from model training on training data,
        with importances calculated using test data (holdout set)"""
        if not isinstance(self._feature_importances_traintest, DataFrame):
            raise Exception(f'Not available: feature importances from training & testing.')
        return self._feature_importances_traintest

    @property
    def feature_importances_reduction_(self) -> DataFrame:
        """Return feature importance from feature reduction, model training on training data,
        with importances calculated using test data (holdout set)"""
        if not isinstance(self._feature_importances_reduction, DataFrame):
            raise Exception(f'Not available: feature importances from feature reduction.')
        return self._feature_importances_reduction

    @property
    def scores_(self) -> dict:
        """Return model scores for model used in gap-filling"""
        if not self._scores:
            raise Exception(f'Not available: model scores for gap-filling.')
        return self._scores

    @property
    def scores_test_(self) -> dict:
        """Return model scores for model trained on training data,
        with scores calculated using test data (holdout set)"""
        if not self._scores_test:
            raise Exception(f'Not available: model scores for gap-filling.')
        return self._scores_test

    @property
    def gapfilling_df_(self) -> DataFrame:
        """Return gapfilled data and auxiliary variables"""
        if not isinstance(self._gapfilling_df, DataFrame):
            raise Exception(f'Gapfilled data not available.')
        return self._gapfilling_df

    @property
    def traintest_details_(self) -> dict:
        """Return details from train/test splits"""
        if not self._traintest_details:
            raise Exception(f'Not available: details about training & testing.')
        return self._traintest_details

    @property
    def accepted_features_(self) -> list:
        """Return list of accepted features from feature reduction"""
        if not self._accepted_features:
            raise Exception(f'Not available: accepted features from feature reduction.')
        return self._accepted_features

    @property
    def rejected_features_(self) -> list:
        """Return list of rejected features from feature reduction"""
        if not self._rejected_features:
            raise Exception(f'Not available: accepted features from feature reduction.')
        return self._rejected_features

    def reduce_features(self):
        """Reduce number of features using permutation importance

        A random variable is added to features and the permutation importances
        are calculated. The permutation importance of the random variable is the
        benchmark to determine whether a feature is relevant. All features where
        permutation importance is smaller or equal to the importance of the random
        variable are rejected.
        """

        df = self.model_df.copy()

        # Info
        print(f"Feature reduction ...")

        # Add random variable as feature
        df, self.random_col = self._add_random_variable(df=df)

        # Data as arrays, y = targets, X = features
        y, X, X_names, timestamp = fr.convert_to_arrays(
            df=df, target_col=self.target_col, complete_rows=True)

        # Train and test set
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.kwargs['random_state'])

        # TODO -------------------------------------------------------------------------->
        # TODO -------------------------------------------------------------------------->
        # TODO -------------------------------------------------------------------------->
        from sklearn.model_selection import TimeSeriesSplit
        splitter = TimeSeriesSplit(n_splits=5)

        from sklearn.model_selection import GridSearchCV
        params = {
            'max_depth': [2, 4, 8],
            'n_estimators': [5, 10, 20],
            'learning_rate': [0.1, 0.05, 0.01],
            'gamma': [0],
            'reg_lambda': [0, 1, 5],
            'early_stopping_rounds': [10],
            'colsample_bytree': [0.3, 0.5, 1],
            'scale_pos_weight': [0.1, 1, 3]
        }
        grid = GridSearchCV(estimator=xgb.XGBRegressor(subsample=0.1),
                            param_grid=params,
                            scoring='neg_mean_squared_error',
                            cv=TimeSeriesSplit(n_splits=10),
                            n_jobs=-1, verbose=1)
        grid.fit(X_train, y_train,
                 eval_set=[(X_train, y_train), (X_test, y_test)],
                 verbose=100)
        grid.best_params_

        # # Plot
        # fig, axs = plt.subplots(10, 1, figsize=(15, 30), sharex=True)
        # fold = 0
        # for train_idx, val_idx in splitter.split(df):
        #     train = df.iloc[train_idx]
        #     test = df.iloc[val_idx]
        #     train[self.target_col].plot(ax=axs[fold], label='Training Set', title=f'Data Train/Test Split Fold {fold}')
        #     test[self.target_col].plot(ax=axs[fold], label='Test Set')
        #     axs[fold].axvline(test.index.min(), color='black', ls='--')
        #     fold += 1
        # plt.show()

        fold = 0
        preds = []
        scores = []
        df = df.dropna()
        for train_idx, val_idx in splitter.split(df):
            train = df.iloc[train_idx]
            test = df.iloc[val_idx]

            features_list = df.columns.tolist()
            features_list.remove(self.target_col)

            X_train = train[features_list]
            y_train = train[self.target_col]

            X_test = test[features_list]
            y_test = test[self.target_col]

            reg = xgb.XGBRegressor(base_score=0.5, booster='gbtree',
                                   n_estimators=1000,
                                   early_stopping_rounds=50,
                                   objective='reg:squarederror',
                                   max_depth=3,
                                   learning_rate=0.02)
            reg.fit(X_train, y_train,
                    early_stopping_rounds=10,
                    eval_set=[(X_train, y_train), (X_test, y_test)],
                    verbose=100)

            y_pred = reg.predict(X_test)
            preds.append(y_pred)
            from sklearn.metrics import mean_squared_error
            score = np.sqrt(mean_squared_error(y_test, y_pred))
            scores.append(score)
            fold += 1

        print(f'Score across folds {np.mean(scores):0.4f}')
        print(f'Fold scores:{scores}')

        # TODO <--------------------------------------------------------------------------
        # TODO <--------------------------------------------------------------------------
        # TODO <--------------------------------------------------------------------------

        # Instantiate model with params
        model = xgb.XGBRegressor(**self.kwargs)
        # model = RandomForestRegressor(**self.kwargs)

        # Train the model
        model.fit(X=X_train, y=y_train)

        # # Predict targets in test data
        # pred_y_test = model.predict(X=X_test)

        # Calculate permutation importance and store in dataframe
        self._feature_importances_reduction = self._permutation_importance(
            model=model, X=X_test, y=y_test, X_names=X_names, showplot_importance=False)

        # Threshold for feature acceptance
        fi_threshold = self.feature_importances_reduction_['PERM_IMPORTANCE'][self.random_col]

        # Get accepted and rejected features
        fidf_accepted = self.feature_importances_reduction_.loc[
            self.feature_importances_reduction_['PERM_IMPORTANCE'] > fi_threshold].copy()
        self._accepted_features = fidf_accepted.index.tolist()
        fidf_rejected = self.feature_importances_reduction_.loc[
            self.feature_importances_reduction_['PERM_IMPORTANCE'] <= fi_threshold].copy()
        self._rejected_features = fidf_rejected.index.tolist()

        # Assemble dataframe for next model
        usecols = [self.target_col]
        usecols = usecols + self._accepted_features
        self.model_df = df[usecols].copy()

        # # This could be a way to combine permutation importance with RFECV,
        # # but at the time of this writing an import failed (Oct 2023)
        # # Train model with random variable included, to detect unimportant features
        # df = df.dropna()
        # targets = df[self.target_col].copy()
        # df = df.drop(self.target_col, axis=1, inplace=False)
        # features = df.copy()
        # estimator = RandomForestRegressor(**self.kwargs)
        # splitter = TimeSeriesSplit(n_splits=10)
        # from eli5.sklearn import PermutationImportance
        # rfecv = RFECV(estimator=PermutationImportance(estimator, scoring='r2', n_iter=10, random_state=42, cv=splitter),
        #               step=1,
        #               min_features_to_select=3,
        #               cv=splitter,
        #               scoring='r2',
        #               verbose=self.verbose,
        #               n_jobs=-1)
        # rfecv.fit(features, targets)
        # # Feature importances
        # features.drop(features.columns[np.where(rfecv.support_ == False)[0]], axis=1, inplace=True)
        # rfecv_fi_df = pd.DataFrame()
        # rfecv_fi_df['FEATURE'] = list(features.columns)
        # rfecv_fi_df['IMPORTANCE'] = rfecv.estimator_.feature_importances_
        # rfecv_fi_df = rfecv_fi_df.set_index('FEATURE')
        # rfecv_fi_df = rfecv_fi_df.sort_values(by='IMPORTANCE', ascending=False)
        # # rfecv.cv_results_
        # # rfecv.n_features_
        # # rfecv.n_features_in_
        # # rfecv.ranking_
        # # rfecv.support_

    def trainmodel(self,
                   showplot_scores: bool = True,
                   showplot_importance: bool = True):
        """
        Train random forest model for gap-filling

        No gap-filling is done here, only the model is trained.

        Args:
            showplot_predictions: shows plot of predicted vs observed
            showplot_importance: shows plot of permutation importances
            verbose: if > 0 prints more text output

        """

        df = self.model_df.copy()

        # Info
        idtxt = f"TRAIN & TEST "
        print(f"Building random forest model based on data between "
              f"{df.index[0]} and {df.index[-1]} ...")

        # Data as arrays
        # y = targets, X = features
        y, X, X_names, timestamp = fr.convert_to_arrays(
            df=df, target_col=self.target_col, complete_rows=True)

        # Train and test set
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.kwargs['random_state'])

        # Instantiate model with params
        self._model = xgb.XGBRegressor(**self.kwargs)
        # self._model = RandomForestRegressor(**self.kwargs)

        # Train the model
        self._model.fit(X=X_train, y=y_train,
                        eval_set=[(X_train, y_train), (X_test, y_test)],
                        # early_stopping_rounds=50,
                        verbose=1)

        # Predict targets in test data
        pred_y_test = self._model.predict(X=X_test)

        # Calculate permutation importance and store in dataframe
        self._feature_importances_traintest = self._permutation_importance(
            model=self._model, X=X_test, y=y_test, X_names=X_names, showplot_importance=showplot_importance)

        # Stats
        self._scores_test = prediction_scores_regr(
            predictions=pred_y_test, targets=y_test, showplot=showplot_scores,
            infotxt=f"{idtxt} trained on training set, tested on test set")

        if showplot_scores:
            plot_prediction_residuals_error_regr(
                model=self._model, X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
                infotxt=f"{idtxt} trained on training set, tested on test set")

        # Collect results
        self._traintest_details = dict(
            X=X,
            y=y,
            timestamp=timestamp,
            predictions=pred_y_test,
            X_names=X_names,
            y_name=self.target_col,
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            model=self._model,
        )

    def fillgaps(self,
                 showplot_scores: bool = True,
                 showplot_importance: bool = True):
        """
        Gap-fill data with previously built model

        No new model is built here, instead the last model built in
        the preceding step .trainmodel() is used.

        y = target
        X = features

        """
        self._fillgaps_fullmodel(showplot_scores, showplot_importance)
        self._fillgaps_fallback()
        self._fillgaps_combinepredictions()

    def report_feature_reduction(self):
        """Results from feature reduction"""

        idtxt = "FEATURE REDUCTION"

        fi = self.feature_importances_reduction_

        # TODO hier weiter

        _X_names = [x for x in fi.index if x != self.random_col]  # Original features without random variable
        print(
            f"\n"
            f"{'=' * len(idtxt)}\n"
            f"{idtxt}\n"
            f"{'=' * len(idtxt)}\n"
            f"\n"
            f"- the random variable {self.random_col} was added to the original features, "
            f"used as benchmark for detecting relevant feature importances\n"
            f"- target variable: {self.target_col}\n"
            f"- features before reduction: {fi.index.to_list()}\n"
            f"- permutation importance was calculated from {self.perm_n_repeats} permutations\n"
            f"- These results are from feature reduction. Note that feature importances for "
            f"the final model are calculated during gap-filling.\n"
            f"\n"
            f"\n"
            f"PERMUTATION IMPORTANCE (FULL RESULTS):\n"
            f"\n"
            f"{fi}"
            f"\n"
            f"\n"
            f"--> {len(fi.index)} input features, "
            f"including {self.random_col}: {fi.index.tolist()}\n"
            f"--> {len(self.accepted_features_)} accepted features, "
            f"larger than {self.random_col}: {self.accepted_features_}\n"
            f"--> {len(self.rejected_features_)} rejected features, "
            f"smaller than or equal to {self.random_col}: {self.rejected_features_}\n"
        )

    def report_traintest(self):
        """Results from model training on test data"""

        idtxt = "MODEL TRAINING & TESTING RESULTS"

        results = self.traintest_details_
        fi = self.feature_importances_traintest_

        test_size_perc = self.test_size * 100
        training_size_perc = 100 - test_size_perc
        n_vals_observed = len(results['y'])
        n_vals_train = len(results['y_train'])
        n_vals_test = len(results['y_test'])
        timestamp = results['timestamp']
        used_features = results['X_names']
        model = results['model']

        print(
            f"\n"
            f"{'=' * len(idtxt)}\n"
            f"{idtxt}\n"
            f"{'=' * len(idtxt)}\n"
            f"\n"
            f"- the model was trained and tested based on data between "
            f"{timestamp[0]} and {timestamp[-1]}.\n"
            f"- in total, {n_vals_observed} observed target values were available for training and testing\n"
            f"- the dataset was split into training and test datasets\n"
            f"  > the training dataset comprised {n_vals_train} target values ({training_size_perc:.1f}%)\n"
            f"  > the test dataset comprised {n_vals_test} target values ({test_size_perc:.1f}%)\n"
            f"\n"
            f"## FEATURE IMPORTANCES\n"
            f"- feature importances were calculated for test data ({n_vals_test} target values).\n"
            f"- permutation importances were calculated from {self.perm_n_repeats} repeats."
            f"\n"
            f"{fi}"
            f"\n"
            f"\n"
            f"## MODEL\n"
            f"The model was trained on the training set.\n"
            f"- estimator:  {model}\n"
            f"- parameters:  {model.get_params()}\n"
            f"- names of features used in model:  {used_features}\n"
            f"- number of features used in model:  {len(used_features)}\n"
            f"\n"
            f"## MODEL SCORES\n"
            f"- the model was trained on training data ({n_vals_train} values).\n"
            f"- the model was tested on test data ({n_vals_test} values).\n"
            f"- all scores were calculated for test split.\n"
            f"  > MAE:  {self.scores_test_['mae']} (mean absolute error)\n"
            f"  > MedAE:  {self.scores_test_['medae']} (median absolute error)\n"
            f"  > MSE:  {self.scores_test_['mse']} (mean squared error)\n"
            f"  > RMSE:  {self.scores_test_['rmse']} (root mean squared error)\n"
            f"  > MAXE:  {self.scores_test_['maxe']} (max error)\n"
            f"  > MAPE:  {self.scores_test_['mape']:.3f} (mean absolute percentage error)\n"
            f"  > R2:  {self.scores_test_['r2']}\n"
        )

    def report_gapfilling(self):
        """Results from gap-filling"""
        # Setup
        idtxt = "GAP-FILLING RESULTS"

        df = self.gapfilling_df_
        model = self.model_
        scores = self.scores_
        fi = self.feature_importances_

        feature_names = fi.index.to_list()
        n_features = len(feature_names)

        locs_observed = df[self.target_gapfilled_flag_col] == 0
        locs_hq = df[self.target_gapfilled_flag_col] == 1
        locs_observed_missing_fromflag = df[self.target_gapfilled_flag_col] > 0
        locs_fallback = df[self.target_gapfilled_flag_col] == 2

        n_observed = locs_observed.sum()
        n_hq = locs_hq.sum()
        n_observed_missing_fromflag = locs_observed_missing_fromflag.sum()
        n_available = len(df[self.target_gapfilled_col].dropna())
        n_potential = len(df.index)
        n_fallback = locs_fallback.sum()
        test_size_perc = self.test_size * 100

        print(
            f"\n"
            f"{'=' * len(idtxt)}\n"
            f"{idtxt}\n"
            f"{'=' * len(idtxt)}\n"
            f"\n"
            f"Model scores and feature importances were calculated from high-quality "
            f"predicted targets ({n_hq} values, {self.target_gapfilled_col} where flag=1) "
            f"in comparison to observed targets ({n_observed} values, {self.target_col}).\n"
            f"\n"
            f"## TARGET\n"
            f"- first timestamp:  {df.index[0]}\n"
            f"- last timestamp:  {df.index[-1]}\n"
            f"- potential number of values: {n_potential} values)\n"
            f"- target column (observed):  {self.target_col}\n"
            f"- missing records (observed):  {df[self.target_col].isnull().sum()} "
            f"(cross-check from flag: {n_observed_missing_fromflag})\n"
            f"- target column (gap-filled):  {self.target_gapfilled_col}  ({n_available} values)\n"
            f"- missing records (gap-filled):  {df[self.target_gapfilled_col].isnull().sum()}\n"
            f"- gap-filling flag: {self.target_gapfilled_flag_col}\n"
            f"  > flag 0 ... observed targets ({n_observed} values)\n"
            f"  > flag 1 ... targets gap-filled with high-quality, all features available ({n_hq} values)\n"
            f"  > flag 2 ... targets gap-filled with fallback ({n_fallback} values)\n"
            f"\n"
            f"## FEATURE IMPORTANCES\n"
            f"- names of features used in model:  {feature_names}\n"
            f"- number of features used in model:  {n_features}\n"
            f"- permutation importances were calculated from {self.perm_n_repeats} repeats.\n"
            f"\n"
            f"{fi}"
            f"\n"
            f"\n"
            f"## MODEL\n"
            f"The model was trained on a training set with test size {test_size_perc:.2f}%.\n"
            f"- estimator:  {model}\n"
            f"- parameters:  {model.get_params()}\n"
            f"\n"
            f"## MODEL SCORES\n"
            f"- MAE:  {scores['mae']} (mean absolute error)\n"
            f"- MedAE:  {scores['medae']} (median absolute error)\n"
            f"- MSE:  {scores['mse']} (mean squared error)\n"
            f"- RMSE:  {scores['rmse']} (root mean squared error)\n"
            f"- MAXE:  {scores['maxe']} (max error)\n"
            f"- MAPE:  {scores['mape']:.3f} (mean absolute percentage error)\n"
            f"- R2:  {scores['r2']}\n"
        )

    def _permutation_importance(self, model, X, y, X_names, showplot_importance) -> DataFrame:
        """Calculate permutation importance"""
        # https://scikit-learn.org/stable/modules/permutation_importance.html#permutation-feature-importance
        fi = permutation_importance(estimator=model,
                                    X=X, y=y,
                                    n_repeats=self.perm_n_repeats,
                                    random_state=42,
                                    scoring='r2',
                                    n_jobs=-1)

        # Store permutation importance
        fidf = pd.DataFrame({'PERM_IMPORTANCE': fi.importances_mean,
                             'PERM_SD': fi.importances_std},
                            index=X_names)

        fidf = fidf.sort_values(by='PERM_IMPORTANCE', ascending=False)

        if showplot_importance:
            fig, axs = plt.subplots(ncols=1, figsize=(9, 16))
            _fidf = fidf.copy().sort_values(by='PERM_IMPORTANCE', ascending=True)
            _fidf['PERM_IMPORTANCE'].plot.barh(color='#008bfb', yerr=_fidf['PERM_SD'], ax=axs)
            axs.set_xlabel("Feature importance")
            axs.set_ylabel("Feature")
            axs.set_title(f"Permutation importance ({self.perm_n_repeats} permutations)")
            axs.legend(loc='lower right')
            fig.tight_layout()
            fig.show()

        return fidf

    def _add_random_variable(self, df: DataFrame) -> tuple[DataFrame, str]:
        # Add random variable as benchmark for relevant feature importances
        random_col = '.RANDOM'  # Random variable as benchmark for relevant importances
        df[random_col] = np.random.RandomState(self.kwargs['random_state']).randn(df.shape[0], 1)
        # df[random_col] = np.random.rand(df.shape[0], 1)
        return df, random_col

    def _lag_features(self):
        """Add lagged variants of variables as new features"""
        return fr.lagged_variants(df=self.model_df,
                                  stepsize=1,
                                  lag=self.features_lag,
                                  exclude_cols=[self.target_col])

    def _check_n_cols(self):
        """Check number of columns"""
        if len(self.model_df.columns) == 1:
            raise Exception(f"(!) Stopping execution because dataset comprises "
                            f"only one single column : {self.model_df.columns}")

    def _fillgaps_fullmodel(self, showplot_scores, showplot_importance):
        """Apply model to fill missing targets for records where all features are available
        (high-quality gap-filling)"""

        # Original input data, contains target and features
        # This dataframe has the full timestamp
        df = self.model_df.copy()

        # Test how the model performs with all y data
        # Since the model was previously trained on test data,
        # here it is checked how well the model performs when
        # predicting all available y data.
        # This is needed to calculate feature importance and scores.
        y, X, X_names, timestamp = fr.convert_to_arrays(
            df=df, target_col=self.target_col, complete_rows=True)

        # Predict all targets (no test split)
        pred_y = self.model_.predict(X=X)

        # Calculate permutation importance and store in dataframe
        self._feature_importances = self._permutation_importance(
            model=self._model, X=X, y=y, X_names=X_names, showplot_importance=showplot_importance)

        # Model scores, using all targets
        self._scores = prediction_scores_regr(predictions=pred_y,
                                              targets=y,
                                              infotxt="trained on training set, "
                                                      "tested on full set",
                                              showplot=showplot_scores)

        # In the next step, all available features are used to
        # predict the target for records where all features are available.
        # Feature data for records where all features are available:
        features_df = df.drop(self.target_col, axis=1)  # Remove target data
        features_df = features_df.dropna()  # Keep rows where all features available
        X = features_df.to_numpy()  # Features are needed as numpy array
        feature_names = features_df.columns.tolist()

        # Predict targets for all records where all features are available
        pred_y = self.model_.predict(X=X)

        # Collect gapfilling results in df
        # Define column names for gapfilled_df
        self._define_cols()

        # Collect predictions in dataframe
        self._gapfilling_df = pd.DataFrame(data={self.pred_fullmodel_col: pred_y}, index=features_df.index)

        # Add target to dataframe
        self._gapfilling_df[self.target_col] = df[self.target_col].copy()

        # Gap locations
        # Make column that contains predicted values
        # for rows where target is missing
        _gap_locs = self._gapfilling_df[self.target_col].isnull()  # Locations where target is missing
        self._gapfilling_df[self.pred_gaps_col] = self._gapfilling_df.loc[
            _gap_locs, self.pred_fullmodel_col]

        # Flag
        # Make flag column that indicates where predictions for
        # missing targets are available, where 0=observed, 1=gapfilled
        # todo Note that missing predicted gaps = 0. change?
        _gapfilled_locs = self._gapfilling_df[self.pred_gaps_col].isnull()  # Non-gapfilled locations
        _gapfilled_locs = ~_gapfilled_locs  # Inverse for gapfilled locations
        self._gapfilling_df[self.target_gapfilled_flag_col] = _gapfilled_locs
        self._gapfilling_df[self.target_gapfilled_flag_col] = self._gapfilling_df[
            self.target_gapfilled_flag_col].astype(
            int)

        # Gap-filled time series
        # Fill missing records in target with predicions
        self._gapfilling_df[self.target_gapfilled_col] = \
            self._gapfilling_df[self.target_col].fillna(self._gapfilling_df[self.pred_fullmodel_col])

        # Restore original full timestamp
        self._gapfilling_df = self._gapfilling_df.reindex(df.index)

        # SHAP values
        # https://pypi.org/project/shap/
        # https://mljar.com/blog/feature-importance-in-random-forest/

    def _fillgaps_fallback(self):

        # Fallback gapfilling
        # Fill still existing gaps in full timestamp data
        # Build fallback model exclusively from timestamp features.
        # Here, the model is trained on the already gapfilled time series,
        # using info from the timestamp, e.g. DOY
        _still_missing_locs = self._gapfilling_df[self.target_gapfilled_col].isnull()
        _num_still_missing = _still_missing_locs.sum()  # Count number of still-missing values
        if _num_still_missing > 0:

            fallback_predictions, \
                fallback_timestamp = \
                self._predict_fallback(series=self._gapfilling_df[self.target_gapfilled_col])

            fallback_series = pd.Series(data=fallback_predictions, index=fallback_timestamp)
            self._gapfilling_df[self.pred_fallback_col] = fallback_series
            self._gapfilling_df[self.target_gapfilled_col] = \
                self._gapfilling_df[self.target_gapfilled_col].fillna(fallback_series)

            self._gapfilling_df.loc[_still_missing_locs, self.target_gapfilled_flag_col] = 2  # Adjust flag, 2=fallback
        else:
            self._gapfilling_df[self.pred_fallback_col] = None

        # Cumulative
        self._gapfilling_df[self.target_gapfilled_cumu_col] = \
            self._gapfilling_df[self.target_gapfilled_col].cumsum()

    def _fillgaps_combinepredictions(self):
        """Combine predictions of full model with fallback predictions"""
        # First add predictions from full model
        self._gapfilling_df[self.pred_col] = self._gapfilling_df[self.pred_fullmodel_col].copy()
        # Then fill remaining gaps with predictions from fallback model
        self._gapfilling_df[self.pred_col] = (
            self._gapfilling_df[self.pred_col].fillna(self._gapfilling_df[self.pred_fallback_col]))

    def _predict_fallback(self, series: pd.Series):
        """Fill data gaps using timestamp features only, fallback for still existing gaps"""
        gf_fallback_df = pd.DataFrame(series)
        gf_fallback_df = include_timestamp_as_cols(df=gf_fallback_df, txt="(ONLY FALLBACK)")

        # Build model for target predictions *from timestamp*
        y_fallback, X_fallback, _, _ = \
            fr.convert_to_arrays(df=gf_fallback_df,
                                 target_col=self.target_gapfilled_col,
                                 complete_rows=True)

        # Instantiate new model with same params as before
        self.kwargs['early_stopping_rounds'] = 0
        model_fallback = xgb.XGBRegressor(**self.kwargs)
        # model_fallback = RandomForestRegressor(**self.kwargs)

        # Train the model on all available records ...
        model_fallback.fit(X=X_fallback, y=y_fallback)

        # ... and use it to predict all records for full timestamp
        full_timestamp_df = gf_fallback_df.drop(self.target_gapfilled_col, axis=1)  # Remove target data
        X_fallback_full = full_timestamp_df.to_numpy()  # Features are needed as numpy array
        pred_y_fallback = model_fallback.predict(X=X_fallback_full)  # Predict targets in test data
        full_timestamp = full_timestamp_df.index

        return pred_y_fallback, full_timestamp

    def _results(self, gapfilled_df, most_important_df, model_r2, still_missing_locs):
        """Summarize gap-filling results"""

        _vals_max = len(gapfilled_df.index)
        _vals_before = len(gapfilled_df[self.target_col].dropna())
        _vals_after = len(gapfilled_df[self.target_gapfilled_col].dropna())
        _vals_fallback_filled = still_missing_locs.sum()
        _perc_fallback_filled = (_vals_fallback_filled / _vals_max) * 100

        print(f"Gap-filling results for {self.target_col}\n"
              f"max possible: {_vals_max} values\n"
              f"before gap-filling: {_vals_before} values\n"
              f"after gap-filling: {_vals_after} values\n"
              f"gap-filled with fallback: {_vals_fallback_filled} values / {_perc_fallback_filled:.1f}%\n"
              f"used features:\n{most_important_df}\n"
              f"predictions vs targets, R2 = {model_r2:.3f}")

    def _define_cols(self):
        self.pred_col = ".PREDICTIONS"
        self.pred_fullmodel_col = ".PREDICTIONS_FULLMODEL"
        self.pred_fallback_col = ".PREDICTIONS_FALLBACK"
        self.pred_gaps_col = ".GAP_PREDICTIONS"
        self.target_gapfilled_col = f"{self.target_col}_gfRF"
        self.target_gapfilled_flag_col = f"FLAG_{self.target_gapfilled_col}_ISFILLED"  # "[0=measured]"
        self.target_gapfilled_cumu_col = ".GAPFILLED_CUMULATIVE"


def example_rfts():
    # Setup, user settings
    # TARGET_COL = 'LE_orig'
    TARGET_COL = 'NEE_CUT_REF_orig'
    subsetcols = [TARGET_COL, 'Tair_f', 'VPD_f', 'Rg_f']

    # from datetime import datetime
    # dt_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # print(f"This page was last modified on: {dt_string}")
    # import importlib.metadata
    # version_diive = importlib.metadata.version("diive")
    # print(f"diive version: v{version_diive}")

    # # Show docstring for QuickFillRFTS
    # print(RandomForestTS.__name__)
    # print(RandomForestTS.__doc__)

    # Example data
    from diive.configs.exampledata import load_exampledata_parquet
    df_orig = load_exampledata_parquet()

    # # Create a large gap
    # remove = df.index.year != 2014
    # # df = df.drop(df.index[100:2200])
    # df = df[remove].copy()

    # Subset
    keep = df_orig.index.year <= 2014
    df = df_orig[keep].copy()
    # df = df_orig.copy()

    # Subset with target and features
    # Only High-quality (QCF=0) measured NEE used for model training in this example
    lowquality = df["QCF_NEE"] > 0
    df.loc[lowquality, TARGET_COL] = np.nan
    df = df[subsetcols].copy()

    # Time series stats
    # from diive.core.dfun.stats import sstats
    # statsdf = sstats(df[TARGET_COL])
    # print(statsdf)

    # from diive.core.plotting.timeseries import TimeSeries  # For simple (interactive) time series plotting
    # TimeSeries(series=df[TARGET_COL]).plot()

    # XGBoost
    # https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster
    xts = XGBoostTS(
        input_df=df,
        target_col=TARGET_COL,
        verbose=1,
        # features_lag=None,
        features_lag=[-1, -1],
        # include_timestamp_as_features=False,
        include_timestamp_as_features=True,
        # add_continuous_record_number=False,
        add_continuous_record_number=True,
        sanitize_timestamp=True,
        perm_n_repeats=9,
        n_estimators=99,
        random_state=42,
        early_stopping_rounds=5,
        max_depth=10,
        learning_rate=0.05,
        colsample_bytree=1,
        n_jobs=-1
    )
    xts.reduce_features()
    xts.report_feature_reduction()

    xts.trainmodel(showplot_scores=False, showplot_importance=False)
    xts.report_traintest()

    xts.fillgaps(showplot_scores=False, showplot_importance=False)
    xts.report_gapfilling()

    observed = df[TARGET_COL]
    gapfilled = xts.get_gapfilled_target()
    # rfts.feature_importances
    # rfts.scores
    # rfts.gapfilling_df

    # # https://www.datacamp.com/tutorial/introduction-to-shap-values-machine-learning-interpretability
    # import shap
    # explainer = shap.TreeExplainer(rfts.model_)
    # xtest = rfts.traintest_details_['X_test']
    # shap_values = explainer.shap_values(xtest)
    # shap.summary_plot(shap_values, xtest)
    # # shap.summary_plot(shap_values[0], xtest)
    # shap.dependence_plot("Feature 12", shap_values, xtest, interaction_index="Feature 11")

    # # Plot
    # from diive.core.plotting.heatmap_datetime import HeatmapDateTime
    # HeatmapDateTime(series=observed).show()
    # HeatmapDateTime(series=gapfilled).show()

    # mds = df_orig['NEE_CUT_REF_f'].copy()
    # mds = mds[mds.index.year >= 2016]
    import matplotlib.pyplot as plt
    # # rfts.gapfilling_df_['.PREDICTIONS_FALLBACK'].cumsum().plot()
    # # rfts.gapfilling_df_['.PREDICTIONS_FULLMODEL'].cumsum().plot()
    # # rfts.gapfilling_df_['.PREDICTIONS'].cumsum().plot()
    xts.get_gapfilled_target().cumsum().plot()
    # mds.cumsum().plot()
    # plt.legend()
    plt.show()

    # d = rfts.gapfilling_df['NEE_CUT_REF_orig'] - rfts.gapfilling_df['.PREDICTIONS']
    # d.plot()
    # plt.show()
    # d = abs(d)
    # d.mean()  # MAE

    print("Finished.")


if __name__ == '__main__':
    # example_quickfill()
    # example_longterm_rfts()
    example_rfts()
    # example_optimize()
