"""
Options back testing tool
"""
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

from src.dutil import get_current_date, last_TH_of_months_between_dates, process_date
from src.hdf5db import hdf5db
from src.log import print_exception, start_logger
from src.columns import STRANGLE_COLUMNS
from src.excel_util import add_style, create_summary_sheet, create_worksheet


class obt(object):
    def __init__(self):
        try:
            start_logger()
            self.db = hdf5db(r"D:/Work/GitHub/hdf5db/indexdb.hdf")
            self.spot = None
            self._symbol = None
            """ Where the module is located """
            self.module_path = os.path.abspath(__file__)
            """ Folder of the module """
            self.module_dir = os.path.dirname(self.module_path)
            """ Output folder of the application """
            self.out_path = Path(self.module_dir).parent.joinpath("output")
            """ Start Date """
            self._ST = None
            """ End Date """
            self._ND = None
            """ Expiry Date """
            self._ED = None
            """ Output data frame, not all the time it has value
            Even it has value no gaurantee it the right output"""
            self.ODF = None
            self.MITR = 5
        except Exception as e:
            print_exception(e)

    @property
    def symbol(self):
        """symbol to be processed"""
        if self._symbol is None:
            raise Exception("Symbol is not yet set.")
        else:
            return self._symbol

    @symbol.setter
    def symbol(self, value):
        self._symbol = value.upper()
        self.db.set_symbol_instrument(self.symbol, "OPTIDX")

    @property
    def ST(self):
        """ Start Date """
        if self._ST is None:
            raise Exception("Start date has not been set.")
        else:
            return self._ST

    @ST.setter
    def ST(self, value):
        self._ST = process_date(value)

    @property
    def ND(self):
        """ End Date """
        if self._ND is None:
            raise Exception("End date has not been set.")
        else:
            return self._ND

    @ND.setter
    def ND(self, value):
        self._ND = process_date(value)

    @property
    def ED(self):
        """ Expiry Date """
        if self._ED is None:
            return self.ND
        else:
            return self._ED

    @ED.setter
    def ED(self, value):
        self._ED = process_date(value)

    def rename_put_columns(self, df):
        df = df.rename(
            columns={
                "CLOSE": "PUT_CLOSE",
                "OPEN_INT": "POI",
                "CHG_IN_OI": "PCOI",
                "STRIKE_PR": "PS",
            }
        )
        return df

    def rename_call_columns(self, df):
        df = df.rename(
            columns={
                "CLOSE": "CALL_CLOSE",
                "OPEN_INT": "COI",
                "CHG_IN_OI": "CCOI",
                "STRIKE_PR": "CS",
            }
        )
        return df

    def get_strike_price(self, df, type, price):
        """Gets the strike for given option type
        and price"""
        si = np.abs(
            df.query("OPTION_TYP==@type and CHG_IN_OI>0")["CLOSE"] - price
        ).idxmin()
        sp = df.loc[si]["STRIKE_PR"]
        return sp

    def calculate_pnl(self, df):
        csp = df.iloc[0]["CALL_CLOSE"]
        # put starting price
        psp = df.iloc[0]["PUT_CLOSE"]
        # total premium
        tp = csp + psp
        df = df.assign(APNL=tp - df[["CALL_CLOSE", "PUT_CLOSE"]].sum(axis=1))
        df = self.calculate_repaired_pnl(df, tp)
        return df
    
    def calculate_repaired_pnl(self, df, tp):
        df = df.assign(TP=tp)
        df = df.assign(PNL=tp - df[["CALL_CLOSE", "PUT_CLOSE"]].sum(axis=1))
        df = df.assign(WIDTH=df.CS - df.PS)
        df = df.assign(UBK=df.CS + tp)
        df = df.assign(LBK=df.PS - tp)
        df = df.assign(UW=df.CS - df.CLOSE)
        df = df.assign(LW=df.CLOSE - df.PS)
        df = df.assign(WR=df.UW / df.LW)
        return df

    def repair_position(self, df, price, itr):
        """ Repairs a position
        Which ever leg is in profit, more than 50% of price
        close it and move to the next strike available at
        the price.
        Do the repair only when any one of the leg is in loss.
        """
        print(f"Repair iteraion {itr}...")
        if itr > self.MITR:
            print(f"Stopping repair iteration since max iteration done...")
            return df
        adj = None
        hp = price / 2
        dfs = df.query("PNL<0 and (PUT_CLOSE<=@hp or CALL_CLOSE<=@hp)")
        if len(dfs) == 0:
            print("No repair required...")
            return df
        #
        dfii = None
        for x in dfs.iloc[0:1].itertuples():
            dfii = x

        if dfii.PUT_CLOSE <= hp:
            print("Adjust put")
            adj = "PUT"
        elif dfii.CALL_CLOSE <= hp:
            print("Adjust call")
            adj = "CALL"
        else:
            print("Unknown issue don't know what to adjust")
        dfc = self.db.get_all_strike_data(dfii.Index, dfii.Index, dfii.ED)
        if adj is "CALL":
            cs = self.get_strike_price(dfc, "CE", price)
            fno = self.db.get_strike_price(dfii.Index, dfii.ED, dfii.ED, "CE", cs)
            fno = self.rename_call_columns(fno)
            df.loc[fno.index, ["CALL_CLOSE", "COI", "CCOI", "CS"]] = fno
            tp = fno["CALL_CLOSE"].iloc[0] + df.loc[fno.index, "TP"].iloc[0] - hp
        elif adj is "PUT":
            ps = self.get_strike_price(dfc, "PE", price)
            fno = self.db.get_strike_price(dfii.Index, dfii.ED, dfii.ED, "PE", ps)
            fno = self.rename_put_columns(fno)
            df.loc[fno.index, ["PUT_CLOSE", "POI", "PCOI", "PS"]] = fno
            tp = fno["PUT_CLOSE"].iloc[0] + df.loc[fno.index, "TP"].iloc[0] - hp
        dfr = self.calculate_repaired_pnl(df.loc[fno.index], tp)
        df.loc[fno.index] = dfr
        return self.repair_position(df, price, itr + 1)

    def build_strangle(self, cs, ps):
        try:
            st = self.ST
            nd = self.ND
            expd = self.ED
            print("Building strangle", end=",")
            print(f" Start : {st:%Y-%m-%d}", end=",")
            print(f" End : {nd:%Y-%m-%d}", end=",")
            print(f" Expiry : {expd:%Y-%m-%d}", end=",")
            print(f" Call : {cs}", end=",")
            print(f" Put : {ps}")
            spot = self.db.get_index_data_between_dates(st, nd)
            fnocs = self.db.get_strike_price(st, nd, expd, "CE", cs)
            fnocs = self.rename_call_columns(fnocs)
            fnops = self.db.get_strike_price(st, nd, expd, "PE", ps)
            fnops = self.rename_put_columns(fnops)
            strangle = spot[["SYMBOL", "CLOSE"]].join([fnocs, fnops])
            # call starting price
            csp = strangle.iloc[0]["CALL_CLOSE"]
            # put starting price
            psp = strangle.iloc[0]["PUT_CLOSE"]
            # total premium
            tp = csp + psp
            strangle = strangle.assign(TP=tp)
            strangle = strangle.assign(
                PNL=tp - strangle[["CALL_CLOSE", "PUT_CLOSE"]].sum(axis=1)
            )
            strangle = strangle.assign(ED=expd)
            strangle = self.calculate_pnl(strangle)
            return strangle[STRANGLE_COLUMNS]
        except Exception as e:
            print_exception(e)
            return None

    def build_strangle_by_price(self, price):
        """
        Creates strangle
        Parameters
        ----------
        st : date
            start date
        nd : date
            end date
        cs : double
            call strike
        ps : double
            put strike
        expd : date
            expiry date - optional
            if expiry date is none, 
            end date is used as expiry date
        Returns
        -------
        Not yet defined
        """
        # start date
        st = self.ST
        # end date
        nd = self.ND
        # expiry date.
        if self.ED is None:
            expd = nd
        else:
            expd = self.ED

        try:
            snd = st + timedelta(days=5)
            df = self.db.get_all_strike_data(st, snd, expd)
            # Get the first group only
            df = df[df["TIMESTAMP"] == df["TIMESTAMP"].unique()[0]]
            cs = self.get_strike_price(df, "CE", price)
            ps = self.get_strike_price(df, "PE", price)
            return self.build_strangle(cs, ps)
        except Exception as e:
            print("Error processing", end="-")
            print(f" st='{st:%Y-%m-%d}'", end=",")
            print(f" nd='{nd:%Y-%m-%d}'", end=",")
            print(f" ed='{expd:%Y-%m-%d}'", end=",")
            print(f" price={price}")
            print_exception(e)
            return None

    def e2e_SSG_by_price(self, num_expiry, price):
        """
        Expiry to expiry strangle creator
        
        Parameters
        ----------
        num_expiry : int
            Number of expirys to process
        price : double
            Strangle to be created at which price
        """
        # Get expiry dates
        # ST - START DATE
        # ED - EXPIRY DATE
        # ND - END DATE
        expd = self.db.get_past_n_expiry_dates(num_expiry, "FUTIDX")
        expd = expd.rename(columns={"EXPIRY_DT": "ED"})
        expd = expd.assign(ST=expd.shift(1) + pd.Timedelta("1Day"))
        expd = expd.assign(ND=expd["ED"])
        expd = expd.dropna().reset_index(drop=True)
        #
        file_name = (
            f"{self.symbol}_strangle_monthly_{num_expiry}_"
            f"price_{price}_"
            f"{datetime.now():%Y-%b-%d_%H-%M-%S}.xlsx"
        )
        full_file_name = Path(self.out_path).joinpath(file_name)
        ewb = pd.ExcelWriter(full_file_name, engine="openpyxl")
        add_style(ewb)
        smry = []
        for x in expd.itertuples():
            try:
                self.ST = x.ST
                self.ND = x.ND
                self.ED = x.ED
                sdf = self.build_strangle_by_price(price)
                rdf = self.repair_position(sdf, price, 1)
                create_worksheet(ewb, rdf, f"{x.ED:%Y-%m-%d}", file_name, index=x.Index)
                smry.append(sdf.iloc[-1])
            except Exception as e:
                print_exception(e)
                print("Error processing last...")
        # save work book
        summary = pd.DataFrame(smry)
        # summary.to_excel(excel_writer=ewb, sheet_name="SUMMARY")
        create_summary_sheet(ewb, summary, file_name)
        ewb.book._sheets.reverse()
        ewb.save()
        print(f"Saved file {full_file_name}")

    def e2e_SSG_SE_by_price(self, st, nd, ed, price):
        """ Creates strangle for single expiry day
        between given start and end days """
        self.ST = st
        self.ND = nd
        self.ED = ed
        sdf = self.build_strangle_by_price(price)
        rdf = self.repair_position(sdf, price, 1)
        file_name = (
            f"{self.symbol}_SSG_"
            f"{self.ST:%Y-%b-%d}_"
            f"{self.ND:%Y-%b-%d}_"
            f"{self.ED:%Y%b%d}"
            f"price_{price}_"
            f"{datetime.now():%Y-%b-%d_%H-%M-%S}.xlsx"
        )
        full_file_name = Path(self.out_path).joinpath(file_name)
        ewb = pd.ExcelWriter(full_file_name, engine="openpyxl")
        add_style(ewb)
        create_worksheet(ewb, sdf, f"{self.ED:%Y-%m-%d}", file_name)
        ewb.save()
        print(f"Saved {full_file_name}")
        self.ODF = rdf
        return rdf

