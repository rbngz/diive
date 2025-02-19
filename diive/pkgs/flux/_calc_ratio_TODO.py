"""
FLUX: CRITICAL HEAT DAYS
========================
"""

from importlib import reload

import numpy as np
import pandas as pd
from matplotlib.legend_handler import HandlerTuple
from pandas import DataFrame

import diive.core.dfun.frames as frames
import diive.core.plotting.styles.LightTheme as theme
import diive.pkgs.analyses.optimumrange
from diive.core.dfun.fits import BinFitterCP
from diive.core.plotting import plotfuncs
from diive.core.plotting.fitplot import fitplot
from diive.core.plotting.rectangle import rectangle
from diive.pkgs.analyses.optimumrange import FindOptimumRange

pd.set_option('display.width', 1500)
pd.set_option('display.max_columns', 30)
pd.set_option('display.max_rows', 30)


class CriticalDays:
    date_col = '.DATE'
    grp_daynight_col = '.GRP_DAYNIGHT'

    def __init__(
            self,
            df: DataFrame,
            x_col: str,
            y_col: str,
            ta_col: str,
            gpp_col:str,
            reco_col:str,
            daynight_split_on: str = 'timestamp',
            daynight_split_day_start_hour: int = 7,
            daynight_split_day_end_hour: int = 18,
            daytime_threshold: int = 20,
            set_daytime_if: str = 'Larger Than Threshold',
            usebins: int = 10,
            bootstrap_runs: int = 10,
            bootstrapping_random_state: int = None
    ):
        """Detect critical heat days from ecosystem fluxes

        XXX

        Args:
            df:
            x_col: Column name of x variable
            y_col: Column name of NEE (net ecosystem exchange, ecosystem flux)
            gpp_col: Column name of GPP (gross primary production, ecosystem flux)
            reco_col: Column name of RECO (ecosystem respiration, ecosystem flux)
            ta_col:
            daynight_split_on: Column name of variable used for detection of daytime and nighttime
            daytime_threshold: Threshold for detection of daytime and nighttime from *daytime_col*
            set_daytime_if: 'Larger Than Threshold' or 'Smaller Than Threshold'
            usebins: XXX (default 10)
            bootstrap_runs: Number of bootstrap runs during detection of
                critical heat days. Must be an odd number. In case an even
                number is given +1 is added automatically.
        """

        if daynight_split_on != 'timestamp':
            self.df = df[[x_col, y_col, gpp_col, reco_col,
                          ta_col, daynight_split_on]].copy()
        else:
            self.df = df[[x_col, y_col, gpp_col, reco_col,
                          ta_col]].copy()
        self.x_col = x_col
        self.nee_col = y_col
        self.gpp_col = gpp_col
        self.reco_col = reco_col
        self.ta_col = ta_col
        self.daynight_split_on = daynight_split_on
        self.daynight_split_day_start_hour = daynight_split_day_start_hour
        self.daynight_split_day_end_hour = daynight_split_day_end_hour
        self.daytime_threshold = daytime_threshold
        self.set_daytime_if = set_daytime_if
        self.usebins = usebins
        self.bootstrapping_random_state = bootstrapping_random_state

        # Number of bootstrap runs must be odd number
        if bootstrap_runs % 2 == 0:
            bootstrap_runs += 1
        self.bootstrap_runs = bootstrap_runs

        # Resample dataset
        aggs = ['mean', 'median', 'count', 'min', 'max', 'sum']
        self.df_aggs = self._resample_dataset(df=self.df, aggs=aggs, day_start_hour=7)

        # Prepare separate daytime and nighttime datasets and aggregate
        self.df_daytime, \
        self.df_daytime_aggs, \
        self.df_nighttime, \
        self.df_nighttime_aggs, = \
            self._prepare_daynight_datasets(aggs=aggs)

        self.predict_min_x = self.df[x_col].min()
        self.predict_max_x = self.df[x_col].max()

        self._results_threshold_detection = {}  # Collects results for each bootstrap run
        self._results_daytime_analysis = {}
        self._results_optimum_range = {}  # Results for optimum range

    @property
    def results_threshold_detection(self) -> dict:
        """Return bootstrap results for daily fluxes, includes threshold detection"""
        if not self._results_threshold_detection:
            raise Exception('Results for threshold detection are empty')
        return self._results_threshold_detection

    @property
    def results_daytime_analysis(self) -> dict:
        """Return bootstrap results for daytime fluxes"""
        if not self._results_daytime_analysis:
            raise Exception('Results for flux analysis are empty')
        return self._results_daytime_analysis

    @property
    def results_optimum_range(self) -> dict:
        """Return results for optimum range"""
        if not self._results_optimum_range:
            raise Exception('Results for optimum range are empty')
        return self._results_optimum_range

    def analyze_daytime(self):
        """Analyze daytime fluxes"""

        # Fit to bootstrapped data, daytime data only, daily time resolution
        # Stored as bootstrap runs > 0 (bts>0)
        bts_results = self._bootstrap_fits(df_aggs=self.df_aggs,  # Daytime and nighttime
                                           x_col=self.x_col,
                                           x_agg='max',
                                           y_cols=[self.nee_col, self.gpp_col, self.reco_col],
                                           y_agg='sum',
                                           ratio_cols=[self.gpp_col, self.reco_col],
                                           fit_to_bins=self.usebins,
                                           detect_zerocrossing=False)

        # Collect GPP:RECO ratios from the different bootstrap runs
        bts_ratios_df = pd.DataFrame()
        for bts in range(1, self.bootstrap_runs + 1):
            ratio_s = bts_results[bts]['ratio_df']['ratio'].copy()
            ratio_s.name = f'bts_{bts}'
            bts_ratios_df = pd.concat([bts_ratios_df, ratio_s], axis=1)
            # bts_ratios_df[bts]=bts_results[bts]['ratio_df']['ratio']
        bts_ratios_df['ROW_Q025'] = bts_ratios_df.quantile(q=.025, axis=1)
        bts_ratios_df['ROW_Q975'] = bts_ratios_df.quantile(q=.975, axis=1)
        bts_ratios_df['fit_x'] = bts_results[1]['ratio_df']['fit_x']  # Add x

        # Get (daytime) GPP and RECO values at detected CHD threshold

        # Threshold from threshold detection
        _thres = self.results_threshold_detection['thres_chd']
        _thres = np.round(_thres, 4)  # Round to 4 digits to facilitate exact search match

        # Get x values from (daytime) GPP and RECO fitting
        _gpp_results = bts_results[0][self.gpp_col]['fit_df']['fit_x'].values
        _gpp_results = np.round(_gpp_results, 4)
        _reco_results = bts_results[0][self.reco_col]['fit_df']['fit_x'].values
        _reco_results = np.round(_reco_results, 4)

        # Find x threshold in x values used in fitting, returns location index
        _gpp_thres_ix = np.where(_gpp_results == _thres)
        _reco_thres_ix = np.where(_reco_results == _thres)

        # Get values from fit at found location
        _gpp_at_thres = bts_results[0][self.gpp_col]['fit_df']['nom'].iloc[_gpp_thres_ix]
        _reco_at_thres = bts_results[0][self.reco_col]['fit_df']['nom'].iloc[_reco_thres_ix]
        _ratio_at_thres = _gpp_at_thres / _reco_at_thres

        daytime_values_at_threshold = {
            'THRESHOLD': _thres,
            'GPP': _gpp_at_thres,
            'RECO': _reco_at_thres,
            'RATIO': _ratio_at_thres
        }

        # Collect results
        self._results_daytime_analysis = dict(bts_results=bts_results,
                                              bts_ratios_df=bts_ratios_df,
                                              daytime_values_at_threshold=daytime_values_at_threshold)

    def detect_chd_threshold(self):
        """Detect critical heat days x threshold for NEE"""

        # Fit to bootstrapped data, daily time resolution
        # Stored as bootstrap runs > 0 (bts>0)
        bts_results = self._bootstrap_fits(df_aggs=self.df_aggs,
                                           x_col=self.x_col,
                                           # x_agg='min',
                                           x_agg='max',
                                           y_cols=[self.nee_col, self.gpp_col, self.reco_col],
                                           y_agg='sum',
                                           ratio_cols=None,
                                           fit_to_bins=self.usebins,
                                           detect_zerocrossing=True)

        # Get flux equilibrium points (RECO = GPP) from bootstrap runs
        bts_zerocrossings_df = self._bts_zerocrossings_collect(bts_results=bts_results)

        # Calc flux equilibrium points aggregates from bootstrap runs
        bts_zerocrossings_aggs = self._zerocrossings_aggs(bts_zerocrossings_df=bts_zerocrossings_df)

        # Threshold for Critical Heat Days (CHDs)
        # defined as the linecrossing max x (e.g. VPD) from bootstrap runs
        thres_chd = bts_zerocrossings_aggs['x_max']

        # Collect days above or equal to CHD threshold
        df_aggs_chds = self.df_aggs.loc[self.df_aggs[self.x_col]['max'] >= thres_chd, :].copy()

        # Number of days above CHD threshold
        num_chds = len(df_aggs_chds)

        # Collect Near-Critical Heat Days (nCHDs)
        # With the number of CHDs known, collect data for the same number
        # of days below of equal to CHD threshold.
        # For example: if 10 CHDs were found, nCHDs are the 10 days closest
        # to the CHD threshold (below or equal to the threshold).
        sortby_col = (self.x_col, 'max')
        nchds_start_ix = num_chds
        nchds_end_ix = num_chds * 2
        df_aggs_nchds = self.df_aggs \
                            .sort_values(by=sortby_col, ascending=False) \
                            .iloc[nchds_start_ix:nchds_end_ix]

        # Threshold for nCHDs
        # The lower threshold is the minimum of found x maxima
        thres_nchds_lower = df_aggs_nchds[self.x_col]['max'].min()
        thres_nchds_upper = thres_chd

        # Number of days above nCHD threshold and below or equal CHD threshold
        num_nchds = len(df_aggs_nchds)

        # Collect results
        self._results_threshold_detection = dict(
            bts_results=bts_results,
            bts_zerocrossings_df=bts_zerocrossings_df,
            bts_zerocrossings_aggs=bts_zerocrossings_aggs,
            thres_chd=thres_chd,
            thres_nchds_lower=thres_nchds_lower,
            thres_nchds_upper=thres_nchds_upper,
            df_aggs_chds=df_aggs_chds,
            df_aggs_nchds=df_aggs_nchds,
            num_chds=num_chds,
            num_nchds=num_nchds
        )

    def find_nee_optimum_range(self):
        # Work w/ daytime data
        opr = FindOptimumRange(df=self.df_daytime, x=self.x_col, y=self.nee_col,
                               define_optimum='min')
        opr.find_optimum()
        self._results_optimum_range = opr.results_optrange()

    def plot_chd_detection_from_nee(self, ax, highlight_year: int = None):
        plot_chd_detection_from_nee(ax=ax, results_chd=self.results_threshold_detection,
                                    y_col=self.nee_col, highlight_year=highlight_year)

    def plot_daytime_analysis(self, ax):
        plot_daytime_analysis(ax=ax,
                              results_chd=self.results_threshold_detection,
                              results_daytime_analysis=self.results_daytime_analysis,
                              gpp_col=self.gpp_col, reco_col=self.reco_col)

    def plot_rolling_bin_aggregates(self, ax):
        """Plot optimum range: rolling bin aggregates"""
        diive.pkgs.analyses.optimumrange.plot_rolling_bin_aggregates(ax=ax, results_optrange=self.results_optimum_range)

    def plot_bin_aggregates(self, ax):
        """Plot optimum range: bin aggregates"""
        diive.pkgs.analyses.optimumrange.plot_bin_aggregates(ax=ax, results_optrange=self.results_optimum_range)

    def plot_vals_in_optimum_range(self, ax):
        """Plot optimum range: values in, above and below optimum per year"""
        diive.pkgs.analyses.optimumrange.plot_vals_in_optimum_range(ax=ax, results_optrange=self.results_optimum_range)

    def _set_fluxcol(self, flux: str = 'nee'):
        fluxcol = None
        if flux == 'nee':
            fluxcol = self.nee_col
        if flux == 'gpp':
            fluxcol = self.gpp_col
        if flux == 'reco':
            fluxcol = self.reco_col
        return fluxcol

    def _resample_dataset(self, df: DataFrame, aggs: list, day_start_hour: int = None):
        """Resample to daily values from *day_start_hour* to *day_start_hour*"""
        df_aggs = df.resample('D', offset=f'{day_start_hour}H').agg(aggs)
        df_aggs = df_aggs.where(df_aggs[self.x_col]['count'] == 48).dropna()  # Full days only
        df_aggs.index.name = 'TIMESTAMP_START'
        return df_aggs

    def _prepare_daynight_datasets(self, aggs):
        """Create separate daytime/nighttime datasets and aggregate"""

        # Get daytime data from dataset
        print("Splitting dataset into daytime and nighttime data ...")
        df, \
        df_daytime, \
        df_nighttime, \
        grp_daynight_col, \
        date_col, \
        flag_daynight_col = frames.splitdata_daynight(
            df=self.df.copy(),
            split_on=self.daynight_split_on,
            # split_day_start_hour=self.daynight_split_day_start_hour,
            # split_day_end_hour=self.daynight_split_day_end_hour,
            split_threshold=self.daytime_threshold,
            split_flagtrue=self.set_daytime_if
        )

        args = dict(groupby_col=grp_daynight_col,
                    date_col=date_col,
                    min_vals=0,
                    aggs=aggs)

        # Aggregate daytime dataset
        print("Aggregating daytime dataset ...")
        df_daytime_aggs = self._aggregate_by_group(df=df_daytime, **args)

        # Aggregate nighttime dataset
        print("Aggregating nighttime dataset ...")
        df_nighttime_aggs = self._aggregate_by_group(df=df_nighttime, **args)

        # print(len(df_daytime_aggs))
        # print(len(df_nighttime_aggs))

        return df_daytime, df_daytime_aggs, df_nighttime, df_nighttime_aggs

    def _zerocrossings_aggs(self, bts_zerocrossings_df: pd.DataFrame) -> dict:
        """Aggregate linecrossing results from bootstrap runs"""
        # linecrossings_x = []
        # linecrossings_y_gpp = []
        # for b in range(1, self.bootstrap_runs + 1):
        #     linecrossings_x.append(self.bts_results[b]['linecrossing_vals']['x_col'])
        #     linecrossings_y_gpp.append(self.bts_results[b]['linecrossing_vals']['gpp_nom'])

        zerocrossings_aggs = dict(
            x_median=round(bts_zerocrossings_df['x_col'].median(), 6),
            x_min=bts_zerocrossings_df['x_col'].min(),
            x_max=bts_zerocrossings_df['x_col'].max(),
            y_nee_median=bts_zerocrossings_df['y_nom'].median(),
            y_nee_min=bts_zerocrossings_df['y_nom'].min(),
            y_nee_max=bts_zerocrossings_df['y_nom'].max(),
        )

        return zerocrossings_aggs

    def _bts_zerocrossings_collect(self, bts_results):
        bts_linecrossings_df = pd.DataFrame()
        for bts in range(1, self.bootstrap_runs + 1):
            _dict = bts_results[bts]['zerocrossing_vals']
            _series = pd.Series(_dict)
            _series.name = bts
            if bts == 1:
                bts_linecrossings_df = pd.DataFrame(_series).T
            else:
                bts_linecrossings_df = bts_linecrossings_df.append(_series.T)
        return bts_linecrossings_df

    def _bootstrap_fits(self,
                        df_aggs: DataFrame,
                        x_col: str,
                        x_agg: str,
                        y_cols: list,
                        y_agg: str,
                        ratio_cols: list = None,
                        fit_to_bins: int = 10,
                        detect_zerocrossing: bool = False) -> dict:
        """Bootstrap ycols and fit to x"""

        # Get column names in aggregated df
        x_col = (x_col, x_agg)
        _y_agg_cols = []
        for _ycol in y_cols:
            _y_agg_cols.append((_ycol, y_agg))
        y_cols = _y_agg_cols
        bts_results = {}
        bts = 0

        while bts < self.bootstrap_runs + 1:
            print(f"Bootstrap run #{bts}")
            fit_results = {}

            if bts > 0:
                # Bootstrap data
                bts_df = df_aggs.sample(n=int(len(df_aggs)), replace=True, random_state=self.bootstrapping_random_state)
            else:
                # First run (bts=0) is with measured data (not bootstrapped)
                bts_df = df_aggs.copy()

            try:
                for y_col in y_cols:

                    # Fit
                    fitter = BinFitterCP(df=bts_df,
                                         x_col=x_col,
                                         y_col=y_col,
                                         num_predictions=1000,
                                         predict_min_x=self.predict_min_x,
                                         predict_max_x=self.predict_max_x,
                                         bins_x_num=fit_to_bins,
                                         bins_y_agg='mean',
                                         fit_type='quadratic')
                    fitter.run()
                    cur_fit_results = fitter.get_results()

                    # Store fit results for current y
                    fit_results[y_col[0]] = cur_fit_results

                    # Zero crossing for NEE
                    if (y_col[0] == self.nee_col) & detect_zerocrossing:
                        zerocrossing_vals = \
                            self._detect_zerocrossing_nee(fit_results_nee=cur_fit_results['fit_df'])

                        if isinstance(zerocrossing_vals, dict):
                            pass
                        else:
                            raise ValueError

                        fit_results['zerocrossing_vals'] = zerocrossing_vals
                        print(fit_results['zerocrossing_vals'])

                    # import matplotlib.pyplot as plt
                    # fit_results['fit_df'][['fit_x', 'nom']].plot()
                    # plt.scatter(fit_results['fit_df']['fit_x'], fit_results['fit_df']['nom'])
                    # plt.scatter(df[x_col], df[y_col])
                    # plt.show()


            except ValueError:
                print(f"(!) WARNING Bootstrap run #{bts} was not successful, trying again")

            # Ratio
            if ratio_cols:
                ratio_df = pd.DataFrame()
                ratio_df['fit_x'] = fit_results[ratio_cols[0]]['fit_df']['fit_x']
                ratio_df[f'{ratio_cols[0]}_nom'] = fit_results[ratio_cols[0]]['fit_df']['nom']
                ratio_df[f'{ratio_cols[1]}_nom'] = fit_results[ratio_cols[1]]['fit_df']['nom']
                ratio_df['ratio'] = ratio_df[f'{ratio_cols[0]}_nom'].div(ratio_df[f'{ratio_cols[1]}_nom'])
                fit_results['ratio_df'] = ratio_df

            # Store bootstrap results in dict
            bts_results[bts] = fit_results
            bts += 1

        return bts_results

    def _detect_zerocrossing_nee(self, fit_results_nee: dict):
        # kudos: https://stackoverflow.com/questions/28766692/intersection-of-two-graphs-in-python-find-the-x-value

        num_zerocrossings = None
        zerocrossings_ix = None

        # Collect predicted vals in df
        zerocrossings_df = pd.DataFrame()
        zerocrossings_df['x_col'] = fit_results_nee['fit_x']
        zerocrossings_df['y_nom'] = fit_results_nee['nom']

        # Check values above/below zero
        _signs = np.sign(zerocrossings_df['y_nom'])
        _signs_max = _signs.max()
        _signs_min = _signs.min()
        _signs_num_totalvals = len(_signs)
        _signs_num_abovezero = _signs.loc[_signs > 0].count()
        _signs_num_belowzero = _signs.loc[_signs < 0].count()

        if _signs_max == _signs_min:
            print("NEE does not cross zero-line.")
        else:
            zerocrossings_ix = np.argwhere(np.diff(_signs)).flatten()
            num_zerocrossings = len(zerocrossings_ix)

        # linecrossings_idx = \
        #     np.argwhere(np.diff(np.sign(zerocrossings_df['gpp_nom'] - zerocrossings_df['reco_nom']))).flatten()
        # num_linecrossings = len(linecrossings_idx)

        # There must be one single line crossing to accept result
        # If there is more than one line crossing, reject result
        if num_zerocrossings > 1:
            return None

        # Values at zero crossing needed
        # Found index is last element *before* zero-crossing, therefore + 1
        zerocrossing_vals = zerocrossings_df.iloc[zerocrossings_ix[0] + 1]
        zerocrossing_vals = zerocrossing_vals.to_dict()

        # NEE at zero crossing must zero or above,
        # i.e. reject if NEE after zero-crossing does not change to emission
        if (zerocrossing_vals['y_nom'] < 0):
            return None

        # x value must be above threshold to be somewhat meaningful, otherwise reject result
        if (zerocrossing_vals['x_col'] < 1):  # TODO currently hardcoded for VPD kPa
            # VPD is too low, must be at least 1 kPa for valid crossing
            return None

        return zerocrossing_vals

    # def _detect_linecrossing(self, gpp_fit_results, reco_fit_results):
    #     # Collect predicted vals in df
    #     linecrossings_df = pd.DataFrame()
    #     linecrossings_df['x_col'] = gpp_fit_results['fit_df']['fit_x']
    #     linecrossings_df['gpp_nom'] = gpp_fit_results['fit_df']['nom']
    #     linecrossings_df['reco_nom'] = reco_fit_results['fit_df']['nom']
    #
    #     # https://stackoverflow.com/questions/28766692/intersection-of-two-graphs-in-python-find-the-x-value
    #     linecrossings_idx = \
    #         np.argwhere(np.diff(np.sign(linecrossings_df['gpp_nom'] - linecrossings_df['reco_nom']))).flatten()
    #
    #     num_linecrossings = len(linecrossings_idx)
    #
    #     # There must be one single line crossing to accept result
    #     if num_linecrossings == 1:
    #
    #         # Flux values at line crossing
    #         linecrossing_vals = linecrossings_df.iloc[linecrossings_idx[0] + 1]
    #
    #         # GPP and RECO must be positive, also x value must be
    #         # above threshold, otherwise reject result
    #         if (linecrossing_vals['gpp_nom'] < 0) \
    #                 | (linecrossing_vals['reco_nom'] < 0) \
    #                 | (linecrossing_vals['x_col'] < 5):
    #             return None
    #
    #         return linecrossing_vals
    #
    #     else:
    #         # If there is more than one line crossing, reject result
    #         return None

    def _aggregate_by_group(self, df, groupby_col, date_col, min_vals, aggs: list) -> pd.DataFrame:
        """Aggregate dataset by *day/night groups*"""

        # Aggregate values by day/night group membership, this drops the date col
        agg_df = \
            df.groupby(groupby_col) \
                .agg(aggs)
        # .agg(['median', q25, q75, 'count', 'max'])
        # .agg(['median', q25, q75, 'min', 'max', 'count', 'mean', 'std', 'sum'])

        # Add the date col back to data
        grp_daynight_col = groupby_col
        agg_df[grp_daynight_col] = agg_df.index

        # For each day/night group, detect its start and end time

        ## Start date (w/ .idxmin)
        grp_starts = df.groupby(groupby_col).idxmin()[date_col].dt.date
        grp_starts = grp_starts.to_dict()
        grp_startdate_col = '.GRP_STARTDATE'
        agg_df[grp_startdate_col] = agg_df[grp_daynight_col].map(grp_starts)

        ## End date (w/ .idxmax)
        grp_ends = df.groupby(groupby_col).idxmax()[date_col].dt.date
        grp_ends = grp_ends.to_dict()
        grp_enddate_col = '.GRP_ENDDATE'
        agg_df[grp_enddate_col] = agg_df[grp_daynight_col].map(grp_ends)

        # Set start date as index
        agg_df = agg_df.set_index(grp_startdate_col)
        agg_df.index = pd.to_datetime(agg_df.index)

        # Keep consecutive time periods with enough values (min. 11 half-hours)
        agg_df = agg_df.where(agg_df[self.x_col]['count'] >= min_vals).dropna()

        return agg_df


def plot_daytime_analysis(ax,
                          results_chd,
                          results_daytime_analysis,
                          gpp_col: str,
                          reco_col: str):
    """Plot daytime fluxes"""

    # For testing: direct plotting
    COLOR_GPP = '#39a7b3'  # blue(500)
    COLOR_RECO = '#d95318'  # red(500)
    COLOR_THRESHOLD = '#FFB72B'  # cyan(4000)
    INFOTXT_FONTSIZE = 11
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    fig = plt.figure(figsize=(10, 10))
    gs = gridspec.GridSpec(1, 1)  # rows, cols
    gs.update(wspace=0, hspace=0, left=.2, right=.8, top=.8, bottom=.2)
    ax = fig.add_subplot(gs[0, 0])

    reload(diive.core.plotting.styles.LightTheme)
    # import diive.core.plotting.styles.LightTheme
    from diive.core.plotting.styles.LightTheme import COLOR_GPP

    units = "$gC\ m^{-2}\ d^{-1}$"

    # Get data
    bts_zerocrossings_aggs = results_chd['bts_zerocrossings_aggs']
    bts_results_daytime = results_daytime_analysis['bts_results'][0]  # 0 means non-bootstrapped data

    # # TODO activate
    # # Ratio GPP:RECO and uncertainty
    # line_ratio, = ax.plot(bts_results_daytime['ratio_df']['fit_x'],
    #                       bts_results_daytime['ratio_df']['ratio'],
    #                       c='black', lw=5, zorder=99, alpha=1, label="ratio GPP:RECO")
    # line_ratio95 = ax.fill_between(results_daytime_analysis['bts_ratios_df']['fit_x'],
    #                                results_daytime_analysis['bts_ratios_df']['ROW_Q025'],
    #                                results_daytime_analysis['bts_ratios_df']['ROW_Q975'],
    #                                alpha=.2, color='black', zorder=89,
    #                                label="95% confidence region")

    # # TODO activate
    # # Threshold lines
    # # Vertical line showing max CHD threshold from bootstrap runs
    # _sub = "$_{CHD}$"
    # line_chd_vertical = ax.axvline(bts_zerocrossings_aggs['x_max'], lw=3, color=COLOR_THRESHOLD, ls='-', zorder=0,
    #                                label=f"THR{_sub}, VPD = {bts_zerocrossings_aggs['x_max']:.1f} hPa")
    # # Vertical line showing xCHD threshold
    # _sub = "$_{XTR}$"
    # # todo currently hardcoded!
    # line_xchd_vertical = ax.axvline(24.112612612612615, lw=3, color=COLOR_THRESHOLD2, ls='-', zorder=0,
    #                                label=f"THR{_sub}, VPD = 24.1 hPa")

    # # TODO activate
    # # Rectangle (bootstrapped results)
    # num_bootstrap_runs = len(results_chd['bts_results'].keys()) - 1  # -1 b/c zero run is non-bootstrapped
    # _sub = "$_{CHD}$"
    # range_bts_netzeroflux = rectangle(ax=ax,
    #                                   rect_lower_left_x=bts_zerocrossings_aggs['x_min'],
    #                                   rect_lower_left_y=0,
    #                                   rect_width=bts_zerocrossings_aggs['x_max'] - bts_zerocrossings_aggs['x_min'],
    #                                   rect_height=1,
    #                                   label=f"THR{_sub} range ({num_bootstrap_runs} bootstraps)",
    #                                   color=COLOR_THRESHOLD, alpha=.2)

    # Secondary axis for fluxes
    ax_twin = ax.twinx()

    # todo act
    # GPP
    # _numvals_per_bin = bts_results_daytime[gpp_col]['numvals_per_bin']
    flux_bts_results = bts_results_daytime[gpp_col]
    line_xy_gpp, line_fit_gpp, line_fit_ci_gpp, line_fit_pb_gpp = \
        fitplot(ax=ax_twin, label=gpp_col,
                # highlight_year=highlight_year,
                flux_bts_results=flux_bts_results, alpha=.2,
                edgecolor=COLOR_GPP, color='none', color_fitline=COLOR_GPP,
                show_prediction_interval=False)

    # # todo act
    # # RECO
    # # _numvals_per_bin = bts_results_daytime[reco_col]['numvals_per_bin']
    # flux_bts_results = bts_results_daytime[reco_col]
    # line_xy_reco, line_fit_reco, line_fit_ci_reco, line_fit_pb_reco = \
    #     fitplot(ax=ax_twin, label=reco_col,
    #             # highlight_year=highlight_year,
    #             flux_bts_results=flux_bts_results, alpha=.2, marker='s',
    #             edgecolor=COLOR_RECO, color='none', color_fitline=COLOR_RECO,
    #             show_prediction_interval=False)

    # Values at threshold

    # # Rectangles
    # kwargs = dict(zorder=97, marker='s', color='none', alpha=1, s=350, lw=3, )
    # scatter_gpp_at_thres = ax_twin.scatter(results_chd['thres_chd'],
    #                                        results_daytime_analysis['daytime_values_at_threshold']['GPP'],
    #                                        edgecolor=COLOR_GPP, label='xxx', **kwargs)
    # scatter_reco_at_thres = ax_twin.scatter(results_chd['thres_chd'],
    #                                         results_daytime_analysis['daytime_values_at_threshold']['RECO'],
    #                                         edgecolor=COLOR_RECO, label='xxx', **kwargs)
    # scatter_ratio_at_thres = ax.scatter(results_chd['thres_chd'],
    #                                     results_daytime_analysis['daytime_values_at_threshold']['RATIO'],
    #                                     edgecolor='black', label='xxx', **kwargs)

    # # Texts: Values at threshold
    # kwargs = dict(alpha=1, horizontalalignment='left', verticalalignment='center',
    #               size=INFOTXT_FONTSIZE)
    # # bbox=dict(boxstyle='square, pad=0', fc='none', ec='none')
    # ax.text(bts_zerocrossings_aggs['x_max'], 0.96, "   Values at threshold:", color='black',
    #         backgroundcolor='white',
    #         transform=ax.get_xaxis_transform(), weight='bold', **kwargs)
    # # t.set_bbox(dict(facecolor='white', alpha=0.5, edgecolor='black'))
    # # GPP at threshold
    # _gpp_at_thres = results_daytime_analysis['daytime_values_at_threshold']['GPP'].values[0]
    # # ax_twin.text(results_chd['thres_chd'], _gpp_at_thres,
    # #              f"{_gpp_at_thres:.0f}", color=COLOR_GPP, backgroundcolor='none', **kwargs)
    # _gpp_at_thres = f"       GPP: {_gpp_at_thres:.2f} {units}"
    # ax.text(bts_zerocrossings_aggs['x_max'], 0.92, _gpp_at_thres, color=COLOR_GPP,
    #         transform=ax.get_xaxis_transform(), weight='normal', **kwargs)
    # # RECO at threshold
    # _reco_at_thres = results_daytime_analysis['daytime_values_at_threshold']['RECO'].values[0]
    # # ax_twin.text(results_chd['thres_chd'], _reco_at_thres,
    # #              f"{_reco_at_thres:.0f}", color=COLOR_RECO, backgroundcolor='none', **kwargs)
    # _reco_at_thres = f"       RECO: {_reco_at_thres:.2f} {units}"
    # ax.text(bts_zerocrossings_aggs['x_max'], 0.89, _reco_at_thres, color=COLOR_RECO, backgroundcolor='none',
    #         transform=ax.get_xaxis_transform(), weight='normal', **kwargs)
    # # Ratio at threshold
    # _ratio_at_thres = results_daytime_analysis['daytime_values_at_threshold']['RATIO'].values[0]
    # # ax.text(results_chd['thres_chd'], _ratio_at_thres,
    # #         f"{_ratio_at_thres:.1f}", color='black', backgroundcolor='none', **kwargs)
    # _ratio_at_thres = f"       ratio: {_ratio_at_thres:.2f}"
    # ax.text(bts_zerocrossings_aggs['x_max'], 0.86, _ratio_at_thres, color='black', backgroundcolor='none',
    #         transform=ax.get_xaxis_transform(), weight='normal', **kwargs)

    ## TODO activate
    # l = ax.legend(
    #     [
    #         # line_chd_vertical,
    #         # range_bts_netzeroflux,
    #         # line_xchd_vertical,
    #         line_ratio,
    #         line_xy_gpp,
    #         line_xy_reco,
    #         line_fit_gpp,
    #         line_fit_reco,
    #         (line_fit_ci_gpp, line_fit_ci_reco),
    #         (line_fit_pb_gpp, line_fit_pb_reco)
    #     ],
    #     [
    #         # line_chd_vertical.get_label(),
    #         # range_bts_netzeroflux.get_label(),
    #         # line_xchd_vertical.get_label(),
    #         line_ratio.get_label(),
    #         line_xy_gpp.get_label(),
    #         line_xy_reco.get_label(),
    #         f"GPP: {line_fit_gpp.get_label()}",
    #         f"RECO: {line_fit_reco.get_label()}",
    #         line_fit_ci_gpp.get_label(),
    #         line_fit_pb_gpp.get_label()
    #     ],
    #     bbox_to_anchor=(0, 1),
    #     frameon=False,
    #     fontsize=FONTSIZE_LEGEND,
    #     loc="lower left",
    #     ncol=2,
    #     scatterpoints=1,
    #     numpoints=1,
    #     handler_map={tuple: HandlerTuple(ndivide=None)})

    # Format
    # ax.axhline(0, lw=1, color='black')
    xlabel = "Daily maximum VPD ($hPa$)"
    ylabel = r"GPP : RECO ($ratio$)"
    # ylabel = r"daily cumulative carbon flux ($\mu mol \/\ CO_2 \/\ m^{-2} \/\ s^{-1}$)"
    plotfuncs.default_format(ax=ax, ax_xlabel_txt=xlabel, ax_ylabel_txt=ylabel,
                             ticks_width=1)

    # Format for secondary y-axis (fluxes)
    from diive.core.plotting.plotfuncs import format_ticks
    format_ticks(ax=ax_twin, width=theme.TICKS_WIDTH, length=theme.TICKS_LENGTH,
                 direction=theme.TICKS_DIRECTION, color='black',
                 labelsize=theme.TICKS_LABELS_FONTSIZE)
    ax_twin.set_ylabel(f'flux ({units})', color=theme.AX_LABELS_FONTCOLOR,
                       fontsize=theme.AX_LABELS_FONTSIZE, fontweight=theme.AX_LABELS_FONTWEIGHT)

    # yticks = ax.yaxis.get_major_ticks()
    # yticks[-1].set_visible(False)
    # yticks = ax_twin.yaxis.get_major_ticks()
    # yticks[-1].set_visible(False)

    ax.text(0.06, 0.95, "(b)",
            size=theme.AX_LABELS_FONTSIZE, color='black', backgroundcolor='none', transform=ax.transAxes,
            alpha=1, horizontalalignment='left', verticalalignment='top')

    fig.show()


def plot_chd_detection_from_nee(ax, results_chd: dict, y_col: str, highlight_year: int = None):
    """Plot results from critical heat days threshold detection"""

    reload(diive.core.plotting.styles.LightTheme)
    # import diive.core.plotting.styles.LightTheme
    from diive.core.plotting.styles.LightTheme import COLOR_GPP, COLOR_THRESHOLD, \
        FONTSIZE_LEGEND, COLOR_THRESHOLD2, COLOR_NEE, INFOTXT_FONTSIZE
    units = "$gC\ m^{-2}\ d^{-1}$"

    # # For testing: direct plotting
    # import matplotlib.pyplot as plt
    # import matplotlib.gridspec as gridspec
    # fig = plt.figure(figsize=(10, 10))
    # gs = gridspec.GridSpec(1, 1)  # rows, cols
    # gs.update(wspace=0, hspace=0, left=.2, right=.8, top=.8, bottom=.2)
    # ax = fig.add_subplot(gs[0, 0])

    bts_results = results_chd['bts_results'][0]  # 0 means non-bootstrapped data
    bts_zerocrossings_aggs = results_chd['bts_zerocrossings_aggs']

    # NEE
    _numvals_per_bin = bts_results[y_col]['numvals_per_bin']
    flux_bts_results = bts_results[y_col]
    line_xy_nee, line_fit_nee, line_fit_ci_nee, line_fit_pb_nee, line_highlight = \
        fitplot(ax=ax,
                label="NEE",
                # label=f"NEE ({_numvals_per_bin['min']:.0f} - {_numvals_per_bin['max']:.0f} values per bin)",
                highlight_year=highlight_year,
                flux_bts_results=flux_bts_results,
                edgecolor='#B0BEC5', color='none', color_fitline=COLOR_NEE,
                show_prediction_interval=True)

    # # Actual non-bootstrapped line crossing, the point where RECO = GPP
    # line_netzeroflux = ax.scatter(bts_results['zerocrossing_vals']['x_col'],
    #                               bts_results['zerocrossing_vals']['y_nom'],
    #                               edgecolor='black', color='none', alpha=1, s=90, lw=2,
    #                               label='net zero flux', zorder=99, marker='s')

    # # Rectangle
    # # Bootstrapped line crossing, the point where RECO = GPP
    # line_bts_median_netzeroflux = ax.scatter(bts_zerocrossings_aggs['x_max'],
    #                                          0,
    #                                          edgecolor=COLOR_NEE, color='none', alpha=1, s=350, lw=3,
    #                                          label='net zero flux (bootstrapped median)', zorder=97, marker='s')

    # Threshold lines
    # Vertical line showing max CHD threshold from bootstrap runs
    _sub = "$_{CHD}$"
    line_chd_vertical = ax.axvline(bts_zerocrossings_aggs['x_max'], lw=3, color=COLOR_THRESHOLD, ls='-', zorder=99,
                                   label=f"THR{_sub}, VPD = {bts_zerocrossings_aggs['x_max']:.1f} hPa")
    # Vertical line showing xCHD threshold
    _sub = "$_{XTR}$"
    # todo currently hardcoded!
    line_xchd_vertical = ax.axvline(24.112612612612615, lw=3, color=COLOR_THRESHOLD2, ls='-', zorder=99,
                                    label=f"THR{_sub}, VPD = 24.1 hPa")

    # Rectangle bootstrap range
    num_bootstrap_runs = len(results_chd['bts_results'].keys()) - 1  # -1 b/c zero run is non-bootstrapped
    _sub = "$_{CHD}$"
    range_bts_netzeroflux = rectangle(ax=ax,
                                      rect_lower_left_x=bts_zerocrossings_aggs['x_min'],
                                      rect_lower_left_y=0,
                                      rect_width=bts_zerocrossings_aggs['x_max'] - bts_zerocrossings_aggs['x_min'],
                                      rect_height=1,
                                      label=f"THR{_sub} range ({num_bootstrap_runs} bootstraps)",
                                      color=COLOR_THRESHOLD)

    # # CHDs
    num_chds = len(results_chd['df_aggs_chds'])
    # area_chd = ax.fill_between([bts_zerocrossings_aggs['x_max'],
    #                             flux_bts_results['fit_df']['fit_x'].max()],
    #                            0, 1,
    #                            color='#BA68C8', alpha=0.1, transform=ax.get_xaxis_transform(),
    #                            label=f"CHDs ({num_chds} days)", zorder=1)
    sym_max = r'$\rightarrow$'
    _pos = bts_zerocrossings_aggs['x_max'] + bts_zerocrossings_aggs['x_max'] * 0.03
    t = ax.text(_pos, 0.07, f"{sym_max} {num_chds} critical heat days", size=INFOTXT_FONTSIZE,
                color='black', backgroundcolor='none', transform=ax.get_xaxis_transform(),
                alpha=1, horizontalalignment='left', verticalalignment='top', zorder=99)
    t.set_bbox(dict(facecolor='white', alpha=.7, edgecolor='black'))

    # # Optimum range (OPDS)
    # area_chd = ax.fill_between([bts_zerocrossings_aggs['x_max'],
    #                             flux_bts_results['fit_df']['fit_x'].max()],
    #                            0, 1,
    #                            color='#BA68C8', alpha=0.1, transform=ax.get_xaxis_transform(),
    #                            label=f"CHDs ({num_chds} days)", zorder=1)

    # Format
    ax.axhline(0, lw=1, color='black')
    xlabel = "Daily maximum VPD ($hPa$)"

    ylabel = f"NEE ({units})"
    plotfuncs.default_format(ax=ax, ax_xlabel_txt=xlabel, ax_ylabel_txt=ylabel)
    # xlim_lower = flux_bts_results['fit_df']['fit_x'].min()
    # ax.set_xlim([-1, flux_bts_results['fit_df']['fit_x'].max()])
    # ax.set_ylim([bts_results['zerocrossing_vals']['y_nom'].min(),
    #              bts_results['zerocrossing_vals']['y_nom'].max()])

    # Custom legend
    # Assign two of the handles to the same legend entry by putting them in a tuple
    # and using a generic handler map (which would be used for any additional
    # tuples of handles like (p1, p3)).
    # https://matplotlib.org/stable/gallery/text_labels_and_annotations/legend_demo.html
    l = ax.legend(
        [
            line_chd_vertical,
            range_bts_netzeroflux,
            line_xchd_vertical,
            line_xy_nee,
            line_highlight,
            line_fit_nee,
            # (line_fit_gpp, line_fit_reco),  # to display two patches next to each other in same line
            line_fit_ci_nee,
            line_fit_pb_nee
        ],
        [
            line_chd_vertical.get_label(),
            range_bts_netzeroflux.get_label(),
            line_xchd_vertical.get_label(),
            line_xy_nee.get_label(),
            line_highlight.get_label(),
            line_fit_nee.get_label(),
            line_fit_ci_nee.get_label(),
            line_fit_pb_nee.get_label()
        ],
        bbox_to_anchor=(0, 1),
        frameon=False,
        fontsize=FONTSIZE_LEGEND,
        loc="lower left",
        ncol=2,
        scatterpoints=1,
        numpoints=1,
        handler_map={tuple: HandlerTuple(ndivide=None)})

    ax.text(0.06, 0.95, "(a)",
            size=theme.AX_LABELS_FONTSIZE, color='black', backgroundcolor='none', transform=ax.transAxes,
            alpha=1, horizontalalignment='left', verticalalignment='top')

    # fig.show()


if __name__ == '__main__':
    pd.options.display.width = None
    pd.options.display.max_columns = None
    pd.set_option('display.max_rows', 3000)
    pd.set_option('display.max_columns', 3000)

    # Test data
    from diive.core.io.files import load_pickle

    df_orig = load_pickle(
        filepath=r'F:\Dropbox\luhk_work\_current\fp2022\7-14__IRGA627572__addingQCF0\CH-DAV_FP2022.1_1997-2022.08_ID20220826234456_30MIN.diive.csv.pickle')

    # Settings
    x_col = 'VPD_f'
    ta_col = 'Tair_f'
    radiation_col = 'PotRad_CUT_REF'
    nee_col = 'NEE_CUT_REF_f'
    gpp_col = 'GPP_DT_CUT_REF'
    reco_col = 'Reco_DT_CUT_REF'
    subset_cols = [x_col, ta_col, radiation_col, nee_col, gpp_col, reco_col]
    df = df_orig[subset_cols].copy().dropna()
    df = df.loc[df.index.year >= 2010]

    # Critical days
    chd = CriticalDays(
        df=df,
        x_col=x_col,
        ta_col=ta_col,
        y_col=nee_col,
        gpp_col=gpp_col,
        reco_col=reco_col,
        daynight_split_on=radiation_col,
        # daynight_split_on='timestamp',
        daytime_threshold=20,
        set_daytime_if='Larger Than Threshold',
        usebins=0,
        bootstrap_runs=3,
        bootstrapping_random_state=None
    )

    # Critical heat days
    chd.detect_chd_threshold()
    # results = chd.results_threshold_detection()

    # # Analyze flux
    # chd.analyze_daytime()
    # # results = chd.results_daytime_analysis()
    #
    # # Plot
    # import matplotlib.gridspec as gridspec
    # import matplotlib.pyplot as plt
    #
    # fig = plt.figure(figsize=(20, 9))
    # gs = gridspec.GridSpec(1, 2)  # rows, cols
    # gs.update(wspace=.2, hspace=1, left=.1, right=.9, top=.85, bottom=.1)
    # ax = fig.add_subplot(gs[0, 0])
    # ax2 = fig.add_subplot(gs[0, 1])
    # chd.plot_chd_detection_from_nee(ax=ax, highlight_year=2019)
    # chd.plot_daytime_analysis(ax=ax2)
    # fig.tight_layout()
    # fig.show()
    #
    # # Optimum range
    # chd.find_nee_optimum_range()
    # import matplotlib.gridspec as gridspec
    # import matplotlib.pyplot as plt
    #
    # fig = plt.figure(figsize=(9, 16))
    # gs = gridspec.GridSpec(3, 1)  # rows, cols
    # # gs.update(wspace=.2, hspace=0, left=.1, right=.9, top=.9, bottom=.1)
    # ax1 = fig.add_subplot(gs[0, 0])
    # ax2 = fig.add_subplot(gs[1, 0])
    # ax3 = fig.add_subplot(gs[2, 0])
    # chd.plot_rolling_bin_aggregates(ax=ax1)
    # chd.plot_bin_aggregates(ax=ax2)
    # chd.plot_vals_in_optimum_range(ax=ax3)
    # fig.show()
    #
    # print("END")

# def detect_chd_threshold_from_partitioned(self):
#
#     # Fit to bootstrapped data
#     # Stored as bootstrap runs > 0 (bts>0)
#     bts_results = self._bootstrap_fits(df=self.df_daytime_aggs,
#                                        x_agg='max',
#                                        y_agg='max',
#                                        fit_to_bins=self.usebins)
#
#     # Get flux equilibrium points (RECO = GPP) from bootstrap runs
#     bts_linecrossings_df = self._bts_linecrossings_collect(bts_results=bts_results)
#
#     # Calc flux equilibrium points aggregates from bootstrap runs
#     bts_linecrossings_aggs = self._linecrossing_aggs(bts_linecrossings_df=bts_linecrossings_df)
#
#     # Threshold for Critical Heat Days (CHDs)
#     # defined as the linecrossing median x (e.g. VPD) from bootstrap runs
#     thres_chd = bts_linecrossings_aggs['x_max']
#
#     # Collect days above or equal to CHD threshold
#     df_daytime_aggs_chds = self.df_daytime_aggs.loc[self.df_daytime_aggs[self.x_col]['max'] >= thres_chd, :].copy()
#
#     # Number of days above CHD threshold
#     num_chds = len(df_daytime_aggs_chds)
#
#     # Collect Near-Critical Heat Days (nCHDs)
#     # With the number of CHDs known, collect data for the same number
#     # of days below of equal to CHD threshold.
#     # For example: if 10 CHDs were found, nCHDs are the 10 days closest
#     # to the CHD threshold (below or equal to the threshold).
#     sortby_col = (self.x_col[0], self.x_col[1], 'max')
#     nchds_start_ix = num_chds
#     nchds_end_ix = num_chds * 2
#     df_daytime_aggs_nchds = self.df_daytime_aggs \
#                                 .sort_values(by=sortby_col, ascending=False) \
#                                 .iloc[nchds_start_ix:nchds_end_ix]
#
#     # Threshold for nCHDs
#     # The lower threshold is the minimum of found x maxima
#     thres_nchds_lower = df_daytime_aggs_nchds[self.x_col]['max'].min()
#     thres_nchds_upper = thres_chd
#
#     # Number of days above nCHD threshold and below or equal CHD threshold
#     num_nchds = len(df_daytime_aggs_nchds)
#
#     # Collect results
#     self._results_threshold_detection = dict(
#         bts_results=bts_results,
#         bts_linecrossings_df=bts_linecrossings_df,
#         bts_linecrossings_aggs=bts_linecrossings_aggs,
#         thres_chd=thres_chd,
#         thres_nchds_lower=thres_nchds_lower,
#         thres_nchds_upper=thres_nchds_upper,
#         df_daytime_aggs_chds=df_daytime_aggs_chds,
#         df_daytime_aggs_nchds=df_daytime_aggs_nchds,
#         num_chds=num_chds,
#         num_nchds=num_nchds
#     )
