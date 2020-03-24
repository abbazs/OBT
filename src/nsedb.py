import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil import parser
from sqlalchemy import MetaData, Table, and_, create_engine, text
from sqlalchemy.sql import asc, column, desc, select

from src import dutil
from src.log import print_exception


class nsedb(object):
    def __init__(self):
        self._SYMBOL = None
        self._INSTRUMENT = None
        self._path = None
        self.db = create_engine("postgresql://postgres@localhost:5432/nsedb")
        self.md = MetaData(self.db)
        self.tfno = None
        self.tidx = None
        self.tvix = Table("vix", self.md, autoload=True)
        pass

    @classmethod
    def get_instance(cls):
        return cls()

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
        self.set_table()

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

    def set_table(self):
        if self.SYMBOL == "NIFTY":
            self.tfno = Table("fno_nifty", self.md, autoload=True)
            self.tidx = Table("idx", self.md, autoload=True)
        elif self.SYMBOL == "BANKNIFTY":
            self.tfno = Table("fno_banknifty", self.md, autoload=True)
            self.tidx = Table("idx", self.md, autoload=True)
        else:
            self.tfno = Table("fno", self.md, autoload=True)
            self.tidx = Table("spot", self.md, autoload=True)

    def get_past_n_expiry_dates(self, n, itype='FUT'):
        try:
            s = self.SYMBOL
            if itype == 'FUT':
                i = self.get_future_instrument()
            else:
                i = self.get_option_instrument() 
            cd = dutil.get_current_date()
            sql_statement = (
                select([column("EXPIRY_DT")])
                .where(
                    and_(
                        self.tfno.c.INSTRUMENT == i,
                        self.tfno.c.SYMBOL == s,
                        self.tfno.c.EXPIRY_DT <= cd,
                    )
                )
                .distinct()
                .order_by(desc(self.tfno.c.EXPIRY_DT))
                .limit(n + 1)
            )
            df = pd.read_sql_query(sql_statement, con=self.db)
            df = df.sort_values("EXPIRY_DT")
            return nsedb.remove_false_expiry(df)
        except Exception as e:
            print_exception(e)

    def get_next_expiry_dates(self):
        try:
            s = self.SYMBOL
            i = self.INSTRUMENT
            cd = dutil.get_current_date()
            sql_statement = (
                select([column("EXPIRY_DT")])
                .where(
                    and_(
                        self.tfno.c.INSTRUMENT == i,
                        self.tfno.c.SYMBOL == s,
                        self.tfno.c.EXPIRY_DT >= cd,
                    )
                )
                .distinct()
            )
            df = pd.read_sql_query(sql_statement, con=self.db)
            return nsedb.remove_false_expiry(df)
        except Exception as e:
            print_exception(e)

    def get_expiry_dates_on_date(self, date):
        try:
            s = self.SYMBOL
            i = self.INSTRUMENT
            ed = dutil.process_date(date)
            st = ed - timedelta(days=5)
            sql_statement = (
                select([column("TIMESTAMP"), column("EXPIRY_DT")])
                .where(
                    and_(
                        self.tfno.c.INSTRUMENT == i,
                        self.tfno.c.SYMBOL == s,
                        self.tfno.c.TIMESTAMP >= st,
                        self.tfno.c.TIMESTAMP <= ed,
                    )
                )
                .distinct()
                .order_by(asc(self.tfno.c.TIMESTAMP))
            )
            df = pd.read_sql_query(sql_statement, con=self.db)
            df = df[df["TIMESTAMP"] == df["TIMESTAMP"].iloc[-1]]
            df = df[df["TIMESTAMP"] != df["EXPIRY_DT"]]
            return nsedb.remove_false_expiry(df)
        except Exception as e:
            print(f"Error processing date {date:%Y-%m-%d}")
            print_exception(e)
            return None

    @staticmethod
    def nr7(dfs):
        try:
            dfx = dfs[["LOW","HIGH"]].diff(axis=1).tail(7)
            nrs = dfx["HIGH"]
            return all(nrs.iloc[0:-1]>=nrs.iloc[-1])
        except Exception as e:
            print_exception(e)
            return False

    def get_index_data_between_dates(self, st, nd):
        try:
            s = self.SYMBOL
            st = dutil.process_date(st)
            ed = dutil.process_date(nd)
            sql_statement = (
                select(["*"])
                .where(
                    and_(
                        self.tidx.c.SYMBOL == s,
                        self.tidx.c.TIMESTAMP >= st,
                        self.tidx.c.TIMESTAMP <= ed,
                    )
                )
                .distinct()
                .order_by(asc(self.tidx.c.TIMESTAMP))
            )
            df = pd.read_sql_query(sql_statement, con=self.db)
            df = df.set_index("TIMESTAMP")
            return df
        except Exception as e:
            print_exception(e)

    def get_vix_data_between_dates(self, st, nd):
        try:
            st = dutil.process_date(st)
            ed = dutil.process_date(nd)
            sql_statement = (
                select(["*"])
                .where(and_(self.tvix.c.TIMESTAMP >= st, self.tvix.c.TIMESTAMP <= ed))
                .distinct()
                .order_by(asc(self.tvix.c.TIMESTAMP))
            )
            df = pd.read_sql_query(sql_statement, con=self.db)
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
            i = self.get_future_instrument()
            st = dutil.process_date(st)
            ed = dutil.process_date(nd)
            expd = dutil.process_date(expd)
            sql_statement = (
                select(
                    [
                        column("TIMESTAMP"),
                        column("CLOSE"),
                        column("OPEN_INT"),
                        column("CHG_IN_OI"),
                    ]
                )
                .where(
                    and_(
                        self.tfno.c.INSTRUMENT == i,
                        self.tfno.c.SYMBOL == s,
                        self.tfno.c.TIMESTAMP >= st,
                        self.tfno.c.TIMESTAMP <= ed,
                        self.tfno.c.EXPIRY_DT == expd,
                    )
                )
                .distinct()
                .order_by(asc(self.tfno.c.TIMESTAMP))
            )
            df = pd.read_sql_query(sql_statement, con=self.db)
            df = df.rename(
                columns={"CLOSE": "FUTURE", "OPEN_INT": "FOI", "CHG_IN_OI": "FCOI"}
            )
            df = df.set_index("TIMESTAMP")
            return df
        except Exception as e:
            print_exception(e)

    def get_strike_price(self, st, nd, expd, opt, strike):
        try:
            s = self.SYMBOL
            i = self.get_option_instrument()
            st = dutil.process_date(st)
            ed = dutil.process_date(nd)
            expd = dutil.process_date(expd)
            sql_statement = (
                select(
                    [
                        column("TIMESTAMP"),
                        column("CLOSE"),
                        column("OPEN_INT"),
                        column("CHG_IN_OI"),
                        column("STRIKE_PR"),
                    ]
                )
                .where(
                    and_(
                        self.tfno.c.INSTRUMENT == i,
                        self.tfno.c.SYMBOL == s,
                        self.tfno.c.TIMESTAMP >= st,
                        self.tfno.c.TIMESTAMP <= ed,
                        self.tfno.c.EXPIRY_DT == expd,
                        self.tfno.c.STRIKE_PR == strike,
                        self.tfno.c.OPTION_TYP == opt,
                    )
                )
                .distinct()
                .order_by(asc(self.tfno.c.TIMESTAMP))
            )
            df = pd.read_sql_query(sql_statement, con=self.db)
            df = df.set_index("TIMESTAMP")
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
            i = self.get_option_instrument()
            st = dutil.process_date(st)
            ed = dutil.process_date(nd)
            expd = dutil.process_date(expd)
            sql_statement = (
                select(["*"])
                .where(
                    and_(
                        self.tfno.c.INSTRUMENT == i,
                        self.tfno.c.SYMBOL == s,
                        self.tfno.c.TIMESTAMP >= st,
                        self.tfno.c.TIMESTAMP <= ed,
                        self.tfno.c.EXPIRY_DT == expd,
                    )
                )
                .distinct()
                .order_by(asc(self.tfno.c.TIMESTAMP))
            )
            df = pd.read_sql_query(sql_statement, con=self.db)
            return df
        except Exception as e:
            print_exception(e)

    def get_option_instrument(self):
        if "NIFTY" not in self.SYMBOL:
            return "OPTSTK"
        else:
            return "OPTIDX"

    def get_future_instrument(self):
        if "NIFTY" not in self.SYMBOL:
            return "FUTSTK"
        else:
            return "FUTIDX"

    @staticmethod
    def remove_false_expiry(df):
        dfr = df.EXPIRY_DT.sort_values()
        false_expirys = (dfr - dfr.shift(1)).dt.days <= 1
        return df[~false_expirys]
