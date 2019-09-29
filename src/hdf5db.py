from datetime import timedelta, datetime, date
from dateutil import parser
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os
from src.log import print_exception
from src import dutil


class hdf5db(object):
    def __init__(self):
        self._SYMBOL = None
        self._INSTRUMENT = None
        self._path = None
        pass

    @classmethod
    def get_instance(cls):
        return cls()

    @classmethod
    def from_path_symbol_instrument(cls, pth, symbol, instrument):
        db = cls()
        db.path = pth
        db.symbol = symbol
        db.instrument = instrument
        return db

    @classmethod
    def from_path(cls, pth):
        db = cls()
        db.path = pth
        return db

    @property
    def SYMBOL(self):
        """symbol to be processed"""
        if self._SYMBOL is None:
            raise Exception("Symbol is not yet set.")
        else:
            return self._SYMBOL

    @SYMBOL.setter
    def SYMBOL(self, value):
        self._SYMBOL = value.upper()

    @property
    def INSTRUMENT(self):
        """instrument to be processed"""
        if self._INSTRUMENT is None:
            raise Exception("Instrument is not yet set.")
        else:
            return self._INSTRUMENT

    @INSTRUMENT.setter
    def INSTRUMENT(self, value):
        self._INSTRUMENT = value.upper()

    def set_symbol_instrument(self, symbol, instrument):
        self.SYMBOL = symbol
        self.INSTRUMENT = instrument

    @property
    def path(self):
        if self._path is None:
            raise Exception("DB path has not been set.")
        else:
            return self._path

    @path.setter
    def path(self, value):
        if value is not None:
            if os.path.exists(value):
                self._path = value
            else:
                raise Exception(f"Unable to find given db in path {value}")
        else:
            raise Exception("Given dbpath is none...")

    def get_past_n_expiry_dates(self, n, instrument=None):
        try:
            s = self.SYMBOL
            if instrument is None:
                i = self.INSTRUMENT
            else:
                i = instrument
            cd = dutil.get_current_date()
            df = pd.read_hdf(
                self.path,
                "fno",
                where="SYMBOL==s and INSTRUMENT==i and EXPIRY_DT<=cd",
                columns=["EXPIRY_DT"],
            ).sort_values("EXPIRY_DT")
            df = df.drop_duplicates().tail(n)
            return hdf5db.remove_false_expiry(df)
        except Exception as e:
            print_exception(e)

    def get_next_expiry_dates(self):
        try:
            s = self.SYMBOL
            i = self.INSTRUMENT
            cd = dutil.get_current_date()
            df = pd.read_hdf(
                self.path,
                "fno",
                where="SYMBOL==s and INSTRUMENT==i and EXPIRY_DT>=cd",
                columns=["EXPIRY_DT"],
            ).sort_values("EXPIRY_DT")
            df = df.drop_duplicates()
            return hdf5db.remove_false_expiry(df)
        except Exception as e:
            print_exception(e)

    def get_expiry_dates_on_date(self, date):
        try:
            s = self.SYMBOL
            i = self.INSTRUMENT
            ed = dutil.process_date(date)
            st = ed - timedelta(days=5)
            dbp = self.path
            df = pd.read_hdf(
                dbp,
                "fno",
                where="SYMBOL==s and INSTRUMENT==i and TIMESTAMP>=st and TIMESTAMP<=ed",
                columns=["TIMESTAMP", "EXPIRY_DT"],
            ).sort_values("TIMESTAMP")
            df = df[df["TIMESTAMP"] == df["TIMESTAMP"].iloc[-1]]
            df = df[df["TIMESTAMP"] != df["EXPIRY_DT"]]
            df = df.sort_values("EXPIRY_DT")
            df = df.drop_duplicates()
            return hdf5db.remove_false_expiry(df)
        except Exception as e:
            print(f"Error processing date {date:%Y-%m-%d}")
            print_exception(e)
            return None

    def get_index_data_between_dates(self, st, nd):
        try:
            s = self.SYMBOL
            std = dutil.process_date(st)
            ndd = dutil.process_date(nd)
            dbp = self.path
            df = pd.read_hdf(
                dbp, "idx", where="SYMBOL==s and TIMESTAMP>=std and TIMESTAMP<=ndd"
            ).sort_values("TIMESTAMP")
            df = df.drop_duplicates()
            df = df.set_index("TIMESTAMP")
            return df
        except Exception as e:
            print_exception(e)

    def get_vix_data_between_dates(self, st, nd):
        try:
            s = self.SYMBOL
            std = dutil.process_date(st)
            ndd = dutil.process_date(nd)
            dbp = self.path
            df = pd.read_hdf(
                dbp, "vix", where="TIMESTAMP>=std and TIMESTAMP<=ndd"
            ).sort_values("TIMESTAMP")
            df = df.drop_duplicates()
            df = df.set_index("TIMESTAMP")
            return df
        except Exception as e:
            print_exception(e)

    def get_vix_data_for_last_n_days(self, n_days):
        try:
            end_date = dutil.get_current_date()
            # Add 5 days to n_days and filter only required number days
            start_date = end_date - timedelta(days=n_days + 5)
            vix_data = self.get_vix_data_between_dates(start_date, end_date)
            st = end_date - timedelta(days=n_days)
            return vix_data[st:]
        except Exception as e:
            print_exception(e)

    def get_index_data_for_last_n_days(self, n_days):
        try:
            end_date = dutil.get_current_date()
            # Add 5 days to n_days and filter only required number days
            start_date = end_date - timedelta(days=n_days + 5)
            spot_data = self.get_index_data_between_dates(start_date, end_date)
            st = end_date - timedelta(days=n_days)
            return spot_data[st:]
        except Exception as e:
            print_exception(e)

    def get_future_price(self, st, nd, expd):
        try:
            s = self.SYMBOL
            i = "FUTIDX"
            st = dutil.process_date(st)
            nd = dutil.process_date(nd)
            expd = dutil.process_date(expd)
            dbp = self.path
            rule = (
                "SYMBOL==s and "
                "INSTRUMENT==i and "
                "TIMESTAMP>=st and "
                "TIMESTAMP<=nd and "
                "EXPIRY_DT==expd"
            )
            df = (
                pd.read_hdf(
                    dbp,
                    "fno",
                    where=rule,
                    columns=["TIMESTAMP", "CLOSE", "OPEN_INT", "CHG_IN_OI"],
                )
                .set_index("TIMESTAMP")
                .sort_index()
            )
            df = df.drop_duplicates()
            df = df.rename(
                columns={"CLOSE": "FUTURE", "OPEN_INT": "FOI", "CHG_IN_OI": "FCOI"}
            )
            return df
        except Exception as e:
            print_exception(e)

    def get_strike_price(self, st, nd, expd, opt, strike):
        try:
            s = self.SYMBOL
            i = "OPTIDX"
            st = dutil.process_date(st)
            nd = dutil.process_date(nd)
            expd = dutil.process_date(expd)
            dbp = self.path
            rule = (
                "SYMBOL==s and "
                "INSTRUMENT==i and "
                "TIMESTAMP>=st and "
                "TIMESTAMP<=nd and "
                "OPTION_TYP==opt and "
                "STRIKE_PR==strike and "
                "EXPIRY_DT==expd"
            )
            df = (
                pd.read_hdf(
                    dbp,
                    "fno",
                    where=rule,
                    columns=[
                        "TIMESTAMP",
                        "CLOSE",
                        "OPEN_INT",
                        "CHG_IN_OI",
                        "STRIKE_PR",
                    ],
                )
                .set_index("TIMESTAMP")
                .sort_index()
            )
            df = df.drop_duplicates()
            return df
        except Exception as e:
            print_exception(e)

    def get_all_strike_data(self, st, nd, expd):
        """
        Gets the strike data between given start and end
        for the given expiry date.
        returns a data frame sorted in ascending order by `TIMESTAMP`
        """
        try:
            s = self.SYMBOL
            i = "OPTIDX"
            st = dutil.process_date(st)
            nd = dutil.process_date(nd)
            expd = dutil.process_date(expd)
            dbp = self.path
            rule = (
                "SYMBOL==s and "
                "INSTRUMENT==i and "
                "TIMESTAMP>=st and "
                "TIMESTAMP<=nd and "
                "EXPIRY_DT==expd"
            )
            df = pd.read_hdf(dbp, "fno", where=rule).sort_values("TIMESTAMP")
            df = df.drop_duplicates()
            return df
        except Exception as e:
            print_exception(e)

    @staticmethod
    def remove_false_expiry(df):
        false_expirys = (df["EXPIRY_DT"] - df["EXPIRY_DT"].shift(1)).dt.days <= 1
        return df[~false_expirys]

    @classmethod
    def get_nifty_instance(cls):
        return cls(
            symbol="nifty", instrument="futidx", pth=r"D:/Work/hdf5db/indexdb.hdf"
        )

