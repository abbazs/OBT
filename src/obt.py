"""
Options back testing tool
"""
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

from src.dutil import get_current_date, last_TH_of_months_between_dates
from src.hdf5db import hdf5db
from src.log import print_exception
from src.columns import STRANGLE_COLUMNS
from src.excel_util import (
    add_style,
    create_summary_sheet,
    create_worksheet,
)


class obt(object):
    def __init__(self):
        try:
            self.db = hdf5db(r"D:/Work/GitHub/hdf5db/indexdb.hdf")
            self.spot = None
            self._symbol = None
            # folder paths
            self.module_path = os.path.abspath(__file__)
            self.module_dir = os.path.dirname(self.module_path)
            self.out_path = Path(self.module_dir).parent.joinpath("output")
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

    def build_strangle(self, st, nd, cs, ps, expd=None):
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
        if expd is None:
            expd = nd
        
        print("Building strangle", end=",")
        print(f" Start : {st:%Y-%m-%d}", end=",")
        print(f" End : {nd:%Y-%m-%d}", end=",")
        print(f" Expiry : {expd:%Y-%m-%d}", end=",")
        print(f" Call : {cs}", end=",")
        print(f" Put : {ps}")
        spot = self.db.get_index_data_between_dates(st, nd)
        fnocs = self.db.get_strike_price(st, nd, expd, "CE", cs)
        fnocs = fnocs.rename(
            columns={
                "CLOSE": "CALL_CLOSE",
                "OPEN_INT": "COI",
                "CHG_IN_OI": "CCOI",
                "STRIKE_PR": "CS",
            }
        )
        fnops = self.db.get_strike_price(st, nd, expd, "PE", ps)
        fnops = fnops.rename(
            columns={
                "CLOSE": "PUT_CLOSE",
                "OPEN_INT": "POI",
                "CHG_IN_OI": "PCOI",
                "STRIKE_PR": "PS",
            }
        )
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
        strangle = strangle.assign(WIDTH=strangle.CS - strangle.PS)
        strangle = strangle.assign(UBK=strangle.CS + tp)
        strangle = strangle.assign(LBK=strangle.PS - tp)
        strangle = strangle.assign(UW=strangle.CS - strangle.CLOSE)
        strangle = strangle.assign(LW=strangle.CLOSE - strangle.PS)
        strangle = strangle.assign(WR=strangle.UW/strangle.LW)
        strangle = strangle.assign(ED=expd)
        return strangle[STRANGLE_COLUMNS]

    def expiry2expiry_strangle(self, num_expiry, price):
        """
        Expirty to expiry strangle creator
        
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
        expd = expd.dropna()
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
                df = self.db.get_all_strike_data(x.ST, x.ST, x.ED)
                csi = np.abs(
                    df.query("OPTION_TYP=='CE' and CHG_IN_OI>0")["CLOSE"] - price
                ).idxmin()
                psi = np.abs(
                    df.query("OPTION_TYP=='PE' and CHG_IN_OI>0")["CLOSE"] - price
                ).idxmin()
                cs = df.loc[csi]["STRIKE_PR"]
                ps = df.loc[psi]["STRIKE_PR"]
                sdf = self.build_strangle(x.ST, x.ND, cs, ps, x.ED)
                create_worksheet(ewb, sdf, f"{x.ED:%Y-%m-%d}", file_name)
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
