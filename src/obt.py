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
            """ Max repair iterations """
            self.MITR = 5
            """ Repair adjustment factor """
            self.RAF = 2
            """ Rapair adjustment trigger """
            self.RAT = 2
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

    def get_expiry_df(self, ne, em):
        # Get expiry dates
        # ST - START DATE
        # ED - EXPIRY DATE
        # ND - END DATE
        expd = self.db.get_past_n_expiry_dates(ne, "FUTIDX")
        expd = expd.rename(columns={"EXPIRY_DT": "ED"})
        expd = expd.assign(ST=expd.shift(em) + pd.Timedelta("1Day"))
        expd = expd.assign(ND=expd["ED"])
        expd = expd.dropna().reset_index(drop=True)
        return expd

    @staticmethod
    def rename_put_columns(df):
        df = df.rename(
            columns={
                "CLOSE": "PUT_CLOSE",
                "OPEN_INT": "POI",
                "CHG_IN_OI": "PCOI",
                "STRIKE_PR": "PS",
            }
        )
        return df

    @staticmethod
    def rename_call_columns(df):
        df = df.rename(
            columns={
                "CLOSE": "CALL_CLOSE",
                "OPEN_INT": "COI",
                "CHG_IN_OI": "CCOI",
                "STRIKE_PR": "CS",
            }
        )
        return df

    @staticmethod
    def get_strike_price(df, type, price):
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
    
    @staticmethod
    def calculate_repaired_pnl(df, tp):
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
        # Repair adjustment trigger
        rat = price / self.RAT
        dfs = df.query("PNL<=0 and (PUT_CLOSE<=@rat or CALL_CLOSE<=@rat)")
        if len(dfs) <= 1:
            print("No repair required...")
            return df
        #
        dfii = None
        for x in dfs.iloc[0:1].itertuples():
            dfii = x

        if dfii.PUT_CLOSE <= rat:
            print("Adjust put")
            adj = "PUT"
            # Calculate adjustment profit earned
            ap = df.iloc[0].PUT_CLOSE - dfii.PUT_CLOSE
        elif dfii.CALL_CLOSE <= rat:
            print("Adjust call")
            adj = "CALL"
            # Calculate adjustment profit earned
            ap = df.iloc[0].CALL_CLOSE - dfii.CALL_CLOSE
        else:
            raise Exception("Unknown issue don't know what to adjust")
        
        # Rapir adjustment price
        rap = self.RAF * price
        print(f"Adjustment profit {ap:.2f}, repair adjustment price {rap:.2f}")
        dfc = self.db.get_all_strike_data(dfii.Index, dfii.Index, dfii.ED)
        if adj is "CALL":
            cs = self.get_strike_price(dfc, "CE", rap)
            fno = self.db.get_strike_price(dfii.Index, dfii.ED, dfii.ED, "CE", cs)
            fno = self.rename_call_columns(fno)
            df.loc[fno.index, ["CALL_CLOSE", "COI", "CCOI", "CS"]] = fno
            tp = fno["CALL_CLOSE"].iloc[0] + df.loc[fno.index, "TP"].iloc[0] + ap
        elif adj is "PUT":
            ps = self.get_strike_price(dfc, "PE", rap)
            fno = self.db.get_strike_price(dfii.Index, dfii.ED, dfii.ED, "PE", ps)
            fno = self.rename_put_columns(fno)
            df.loc[fno.index, ["PUT_CLOSE", "POI", "PCOI", "PS"]] = fno
            tp = fno["PUT_CLOSE"].iloc[0] + df.loc[fno.index, "TP"].iloc[0] + ap
        dfr = self.calculate_repaired_pnl(df.loc[fno.index], tp)
        df.loc[fno.index] = dfr
        return self.repair_position(df, price, itr + 1)

    def build_strangle(self, cs, ps, cpr=None, ppr=None):
        try:
            st = self.ST
            nd = self.ND
            expd = self.ED
            print("Building strangle", end=",")
            print(f" Start : {st:%Y-%m-%d}", end=",")
            print(f" End : {nd:%Y-%m-%d}", end=",")
            print(f" Expiry : {expd:%Y-%m-%d}", end=",")
            print(f" Call : {cs}", end=",")
            print(f" Put : {ps}", end=",")
            print(f" CallPr : {cpr}", end=",")
            print(f" PutPr : {ppr}")
            spot = self.db.get_index_data_between_dates(st, nd)
            fnocs = self.db.get_strike_price(st, nd, expd, "CE", cs)
            fnocs = self.rename_call_columns(fnocs)
            fnops = self.db.get_strike_price(st, nd, expd, "PE", ps)
            fnops = self.rename_put_columns(fnops)
            strangle = spot[["SYMBOL", "CLOSE"]].join([fnocs, fnops])
            # call starting price
            if cpr is not None:
                strangle["CALL_CLOSE"].iat[0] = cpr
            csp = strangle.iloc[0]["CALL_CLOSE"]
            # put starting price
            if ppr is not None:
                strangle["PUT_CLOSE"].iat[0] = ppr
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

    def get_atm_strike(self):
        """
        Returns the atm strike
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
            opg = df.groupby("OPTION_TYP")
            opc = opg.get_group("CE").drop("OPTION_TYP", axis=1).set_index("TIMESTAMP")
            opc = opc[opc.index == opc.index[0]]
            opp = opg.get_group("PE").drop("OPTION_TYP", axis=1).set_index("TIMESTAMP")
            opp = opp[opp.index == opp.index[0]]
            opm = opc.merge(
                opp,
                how="inner",
                left_index=True,
                on=["STRIKE_PR"],
                suffixes=["_C", "_P"],
            )
            # Starting day may not be a trading day, hence do this.
            idx = (
                (opm["CLOSE_C"] - opm["CLOSE_P"])
                .abs()
                .reset_index(drop=True)
                .idxmin()
            )
            atm_strike = opm["STRIKE_PR"].iloc[idx]
            print(f"ATM strike price {atm_strike:.0f}")
            return atm_strike
        except Exception as e:
            print("Error getting atm strike ", end="-")
            print(f" st='{st:%Y-%m-%d}'", end=",")
            print(f" nd='{nd:%Y-%m-%d}'", end=",")
            print(f" ed='{expd:%Y-%m-%d}'", end=",")
            print_exception(e)
            return None


    def e2e_SSG_by_price(self, num_expiry, price, exp_month=1):
        """
        Expiry to expiry strangle creator
        
        Parameters
        ----------
        num_expiry : int
            Number of expirys to process
        price : double
            Strangle to be created at which price
        """
        expd = self.get_expiry_df(num_expiry, exp_month)
        #
        file_name = (
            f"{self.symbol}_SSG_{num_expiry}_"
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
            f"{self.ED:%Y-%b-%d}"
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

    def e2e_SSG_SE_custom(self, conf):
        """ Creates strangle for single expiry day
        between given start and end days """
        self.ST = conf["ST"]
        self.ND = conf["ND"]
        self.ED = conf["ED"]
        sdf = self.build_strangle(conf["CS"], conf["PS"], conf["CPR"], conf["PPR"])
        if (conf["CPR"] is not None) and (conf["PPR"] is not None):
            price = (conf["CPR"] + conf["PPR"])/2
        else:
            price = sdf["TP"].iloc[0]/2
        rdf = self.repair_position(sdf, price, 1)
        file_name = (
            f"{self.symbol}_SSG_custom_"
            f"{self.ED:%Y-%b-%d}"
            f"price_{price:.2f}_"
            f"{datetime.now():%Y-%b-%d_%H-%M-%S}.xlsx"
        )
        full_file_name = Path(self.out_path).joinpath(file_name)
        ewb = pd.ExcelWriter(full_file_name, engine="openpyxl")
        add_style(ewb)
        create_worksheet(ewb, sdf, f"{self.ED:%Y-%m-%d}", file_name)
        ewb.save()
        print(f"Saved {full_file_name}")
        self.ODF = sdf
        return sdf
    
    def e2e_SSR(self, num_expiry, price, exp_month=1):
        """
        Expiry to expiry strangle creator
        
        Parameters
        ----------
        num_expiry : int
            Number of expirys to process
        price : double
            Strangle to be created at which price
        """
        expd = self.get_expiry_df(num_expiry, exp_month)
        #
        file_name = (
            f"{self.symbol}_STR_{num_expiry}_"
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
                strike = self.get_atm_strike()
                sdf = self.build_strangle(strike, strike)
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