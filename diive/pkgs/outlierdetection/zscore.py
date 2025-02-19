"""
OUTLIER DETECTION: Z-SCORE TESTS
================================

This module is part of the diive library:
https://github.com/holukas/diive

kudos:
    - https://www.analyticsvidhya.com/blog/2022/08/outliers-pruning-using-python/

"""

import numpy as np
import pandas as pd
from pandas import Series, DatetimeIndex

import diive.core.funcs.funcs as funcs
from diive.core.base.flagbase import FlagBase
from diive.core.times.times import DetectFrequency
from diive.core.utils.prints import ConsoleOutputDecorator
from diive.pkgs.createvar.daynightflag import DaytimeNighttimeFlag


@ConsoleOutputDecorator()
class zScoreDaytimeNighttime(FlagBase):
    flagid = 'OUTLIER_ZSCOREDTNT'

    def __init__(self,
                 series: Series,
                 lat: float,
                 lon: float,
                 utc_offset: int,
                 idstr: str = None,
                 thres_zscore: float = 4,
                 showplot: bool = False,
                 verbose: bool = False):
        """Identify outliers based on the z-score or series records, separately for daytime and nighttime.

        Args:
            series: Time series in which outliers are identified.
            lat: Latitude of location as float, e.g. 46.583056
            lon: Longitude of location as float, e.g. 9.790639
            utc_offset: UTC offset of *timestamp_index*, e.g. 1 for UTC+01:00
                The datetime index of the resulting Series will be in this timezone.
            idstr: Identifier, added as suffix to output variable names.
            thres_zscore: Threshold for z-score, scores above this value will be flagged as outlier.
            showplot: Show plot with results from the outlier detection.
            verbose: Print more text output.

        Returns:
            Flag series that combines flags from all iterations in one single flag.

        """
        super().__init__(series=series, flagid=self.flagid, idstr=idstr)
        self.showplot = False
        self.verbose = False
        self.thres_zscore = thres_zscore
        self.showplot = showplot
        self.verbose = verbose

        # Make sure time series has frequency
        # Freq is needed for the detection of daytime/nighttime from lat/lon
        if not self.series.index.freq:
            freq = DetectFrequency(index=self.series.index, verbose=True).get()
            self.series = self.series.asfreq(freq)

        # Detect nighttime
        dnf = DaytimeNighttimeFlag(
            timestamp_index=self.series.index,
            nighttime_threshold=50,
            lat=lat,
            lon=lon,
            utc_offset=utc_offset)
        daytime = dnf.get_daytime_flag()
        nighttime = dnf.get_nighttime_flag()
        self.is_daytime = daytime == 1  # Convert 0/1 flag to False/True flag
        self.is_nighttime = nighttime == 1  # Convert 0/1 flag to False/True flag

    def calc(self, repeat: bool = True):
        """Calculate overall flag, based on individual flags from multiple iterations.

        Args:
            repeat: If *True*, the outlier detection is repeated until all
                outliers are removed.

        """

        self._overall_flag, n_iterations = self.repeat(func=self.run_flagtests, repeat=repeat)
        if self.showplot:
            self.defaultplot(n_iterations=n_iterations)

    def _flagtests(self, iteration) -> tuple[DatetimeIndex, DatetimeIndex, int]:
        """Perform tests required for this flag"""

        # Working data
        s = self.filteredseries.copy().dropna()
        # s = self.series.copy().dropna()
        flag = pd.Series(index=s.index, data=np.nan)
        # flag = pd.Series(index=self.series.index, data=np.nan)

        # Run for daytime (dt)
        _s_dt = s[self.is_daytime].copy()  # Daytime data
        _zscore_dt = funcs.zscore(series=_s_dt)
        _ok_dt = _zscore_dt <= self.thres_zscore
        _ok_dt = _ok_dt[_ok_dt].index
        _rejected_dt = _zscore_dt > self.thres_zscore
        _rejected_dt = _rejected_dt[_rejected_dt].index

        # Run for nighttime (nt)
        _s_nt = s[self.is_nighttime].copy()  # Daytime data
        _zscore_nt = funcs.zscore(series=_s_nt)
        _ok_nt = _zscore_nt <= self.thres_zscore
        _ok_nt = _ok_nt[_ok_nt].index
        _rejected_nt = _zscore_nt > self.thres_zscore
        _rejected_nt = _rejected_nt[_rejected_nt].index

        # Collect daytime and nighttime flags in one overall flag
        flag.loc[_ok_dt] = 0
        flag.loc[_rejected_dt] = 2
        flag.loc[_ok_nt] = 0
        flag.loc[_rejected_nt] = 2

        n_outliers = (flag == 2).sum()

        ok = (flag == 0)
        ok = ok[ok].index
        rejected = (flag == 2)
        rejected = rejected[rejected].index

        if self.verbose:
            print(f"ITERATION#{iteration}: Total found outliers: "
                  f"{n_outliers} (daytime+nighttime), "
                  f"{len(_rejected_dt)} (daytime), "
                  f"{len(_rejected_nt)} (nighttime)")

        return ok, rejected, n_outliers


@ConsoleOutputDecorator()
class zScore(FlagBase):
    flagid = 'OUTLIER_ZSCORE'

    def __init__(self,
                 series: Series,
                 idstr: str = None,
                 thres_zscore: float = 4,
                 showplot: bool = False,
                 plottitle: str = None,
                 verbose: bool = False):
        """Identify outliers based on the z-score of records.

        Args:
            series: Time series in which outliers are identified.
            idstr: Identifier, added as suffix to output variable names.
            thres_zscore: Threshold for z-score, scores above this value will be flagged as outlier.
            showplot: Show plot with results from the outlier detection.
            plottitle: Title string for the plot.
            verbose: Print more text output.

        Returns:
            Flag series that combines flags from all iterations in one single flag.

        """
        super().__init__(series=series, flagid=self.flagid, idstr=idstr)
        self.showplot = False
        self.plottitle = None
        self.verbose = False
        self.thres_zscore = thres_zscore
        self.showplot = showplot
        self.plottitle = plottitle
        self.verbose = verbose

    def calc(self, repeat: bool = True):
        """Calculate overall flag, based on individual flags from multiple iterations.

        Args:
            repeat: If *True*, the outlier detection is repeated until all
                outliers are removed.

        """
        self._overall_flag, n_iterations = self.repeat(self.run_flagtests, repeat=repeat)
        if self.showplot:
            self.defaultplot(n_iterations=n_iterations)

    def _flagtests(self, iteration) -> tuple[DatetimeIndex, DatetimeIndex, int]:
        """Perform tests required for this flag"""

        # Working data
        s = self.filteredseries.copy().dropna()

        # Run with threshold
        zscores = funcs.zscore(series=s)
        ok = zscores <= self.thres_zscore
        ok = ok[ok].index
        rejected = zscores > self.thres_zscore
        rejected = rejected[rejected].index

        n_outliers = len(rejected)

        if self.verbose:
            print(f"ITERATION#{iteration}: Total found outliers: {len(rejected)} values")
        # print(f"z-score of {threshold} corresponds to a prob of {100 * 2 * norm.sf(threshold):0.2f}%")

        return ok, rejected, n_outliers


def example():
    from diive.configs.exampledata import load_exampledata_parquet
    df = load_exampledata_parquet()
    series = df['Tair_f'].copy()

    # series = series.iloc[0:1000].copy()

    zdn = zScoreDaytimeNighttime(
        series=series,
        lat=47.286417,
        lon=7.733750,
        utc_offset=1,
        thres_zscore=2.5,
        showplot=True,
        verbose=True)

    zdn.calc(repeat=True)
    iterations_df = zdn.get_flag()
    iterations_df.to_csv(r"C:\Users\nopan\Desktop\temp.csv")
    print("XXX")

    # from diive.core.plotting.heatmap_datetime import HeatmapDateTime
    # HeatmapDateTime(series=zdn['Tair_f']).show()
    # HeatmapDateTime(series=zdn['FLAG_Tair_f_OUTLIER_ZSCOREDTNT_ITER1_TEST']).show()


if __name__ == '__main__':
    example()
    # help(zScoreDaytimeNighttime)
    # help(zScoreDaytimeNighttime.__init__)
