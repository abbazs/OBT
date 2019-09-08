"""
Options back testing tool
"""
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.columns import POSITION_COLUMNS
from src.dutil import get_current_date, last_TH_of_months_between_dates, process_date
from src.excel_util import add_style, create_summary_sheet, create_worksheet
from src.hdf5db import hdf5db
from src.log import print_exception, start_logger


class obt(object):
    def __init__(self):
        try:
            start_logger()
            self.db = hdf5db.from_path(r"D:/Work/GitHub/hdf5db/indexdb.hdf")
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
            """ Strangle or straddle adjustment factor """
            self.SSAF = 2
            """ No adjustment if the number of days to expiry is less than NOAD """
            self.NOAD = 5
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
            df.query("OPTION_TYP==@type and OPEN_INT>0 and CHG_IN_OI!=0")["CLOSE"]
            - price
        ).idxmin()
        sp = df.loc[si]["STRIKE_PR"]
        return sp

    def calculate_pnl(self, df):
        csp = df.iloc[0]["CALL_CLOSE"]
        # put starting price
        psp = df.iloc[0]["PUT_CLOSE"]
        # total premium
        tp = csp + psp
        # APNL - Actual profit and loss with out adjustments
        df = df.assign(APNL=tp - df[["CALL_CLOSE", "PUT_CLOSE"]].sum(axis=1))
        df = self.calculate_repaired_pnl(df, tp)
        return df

    def calculate_repaired_pnl(self, df, tp):
        df = df.assign(TP=tp)
        df = df.assign(PNL=tp - df[["CALL_CLOSE", "PUT_CLOSE"]].sum(axis=1))
        df = df.assign(WIDTH=df.CS - df.PS)
        df = df.assign(UBK=df.CS + tp)
        df = df.assign(LBK=df.PS - tp)
        df = df.assign(CBK=df.CS + (tp * self.SSAF))
        df = df.assign(PBK=df.PS - (tp * self.SSAF))
        df = df.assign(UW=df.CS - df.SPOT)
        df = df.assign(LW=df.SPOT - df.PS)
        df = df.assign(WR=df.UW / df.LW)
        return df

    def repair_strangle(self, df, price, itr):
        """ Repairs a strangle position
        Which ever leg is in profit, more than 50% of price
        close it and move to the next strike available at
        the price.
        Do the repair only when any one of the leg is in loss.
        """
        print(
            f"Repair iteraion ({itr}) : price = {price:.2f} : date {self.ST:%Y-%m-%d}"
        )
        if itr > self.MITR:
            print(f"Stopping repair iteration since max iteration done...")
            return df
        sdf = df[self.ST :]
        dfk = sdf.iloc[0]
        # Repair adjustment trigger
        rat = price * self.SSAF
        dfs = sdf.query("PUT_CLOSE>=@rat or CALL_CLOSE>=@rat")
        if len(dfs) == 0:
            print(f"Not adjusting any further position in control...")
            return df
        else:
            dfii = dfs.iloc[0]
            self.ST = dfii.name
            dfr = df[self.ST :]
            if len(dfr) <= self.NOAD:
                print("No repair required...")
                return df
        #
        # Calculate adjustment profit and loss
        if dfii.PUT_CLOSE >= rat:
            print("Put adjustment")
            # Adjustment loss
            adl = dfk.PUT_CLOSE - dfii.PUT_CLOSE
            # Adjustment proift
            adp = dfk.CALL_CLOSE - dfii.CALL_CLOSE
            # New price to be adjusted for
            call_price = rat  # Move call twice the price
            put_price = price  # Move put for the same price
        elif dfii.CALL_CLOSE >= rat:
            print("Call adjustment")
            # Adjustment loss
            adl = dfk.CALL_CLOSE - dfii.CALL_CLOSE
            # Adjustment proift
            adp = dfk.PUT_CLOSE - dfii.PUT_CLOSE
            # New price to be adjusted for
            call_price = price  # Move call for same price
            put_price = rat  # Move put for twice the price
        else:
            raise Exception("Unknown issue don't know what to adjust")

        print(f"Adjustment profit {adp:.2f}")
        print(f"Adjustment loss {adl:.2f}")
        print(f"New call price {call_price:.2f}")
        print(f"New put price {put_price:.2f}")
        dfc = self.db.get_all_strike_data(dfii.name, dfii.name, dfii.ED)
        # Adjust call
        cs = self.get_strike_price(dfc, "CE", call_price)
        fno = self.db.get_strike_price(dfii.name, dfii.ED, dfii.ED, "CE", cs)
        fno = self.rename_call_columns(fno)
        df.loc[fno.index, ["CALL_CLOSE", "COI", "CCOI", "CS"]] = fno
        # Adjust put
        ps = self.get_strike_price(dfc, "PE", put_price)
        fno = self.db.get_strike_price(dfii.name, dfii.ED, dfii.ED, "PE", ps)
        fno = self.rename_put_columns(fno)
        df.loc[fno.index, ["PUT_CLOSE", "POI", "PCOI", "PS"]] = fno
        # calculate new target profit
        tpl = df.loc[fno.index, ["CALL_CLOSE", "PUT_CLOSE"]].iloc[0]
        tp = tpl.sum() + adl + adp
        #
        dfr = self.calculate_repaired_pnl(df.loc[fno.index], tp)
        df.loc[fno.index] = dfr
        df.loc[fno.index, "ADN"] = itr
        return self.repair_strangle(df, rat, itr + 1)

    def repair_straddle(self, df, itr):
        """ Repairs a straddle position
        """
        print(f"Repair iteraion ({itr}) : date {self.ST:%Y-%m-%d}")
        if itr > self.MITR:
            print(f"Stopping repair iteration since max iteration done...")
            return df
        # Do not adjust if last adjustment is less than NOAD
        adns = df[:self.ST]["ADN"].unique()
        adn = adns[-1]
        adnl = len(df[:self.ST].query("ADN==@adn"))
        if adnl <= self.NOAD:
            nmov = self.NOAD - adnl
            self.ST = df[self.ST:].index[nmov]
        # dfloc
        sdf = df[self.ST:]
        dfk = sdf.iloc[0]
        dfs = sdf.query("SPOT>@dfk.CBK or SPOT<@dfk.PBK")
        if len(dfs) == 0:
            print(f"Not adjusting any further position in control...")
            return df
        else:
            dfii = dfs.iloc[0]
            self.ST = dfii.name
            dfr = df[self.ST:]
            if len(dfr) <= self.NOAD:
                print(
                    f"Not adjusting any further days to expiry is less than ({len(dfr)})..."
                )
                return df
        atm = self.get_atm_strike()
        # Adjust Call
        fno = self.db.get_strike_price(dfii.name, dfii.ED, dfii.ED, "CE", atm.STRIKE_PR)
        fno = self.rename_call_columns(fno)
        df.loc[fno.index, ["CALL_CLOSE", "COI", "CCOI", "CS"]] = fno
        # Adjust Put
        fno = self.db.get_strike_price(dfii.name, dfii.ED, dfii.ED, "PE", atm.STRIKE_PR)
        fno = self.rename_put_columns(fno)
        df.loc[fno.index, ["PUT_CLOSE", "POI", "PCOI", "PS"]] = fno
        # Calculate new target profit
        tpl = df.loc[fno.index, ["CALL_CLOSE", "PUT_CLOSE"]].iloc[0]
        adp = dfk.PUT_CLOSE - dfii.PUT_CLOSE
        adc = dfk.CALL_CLOSE - dfii.CALL_CLOSE
        tp = tpl.sum() + adp + adc
        #
        dfr = self.calculate_repaired_pnl(df.loc[fno.index], tp)
        df.loc[fno.index] = dfr
        df.loc[fno.index, "ADN"] = itr
        return self.repair_straddle(df, itr + 1)

    def build_ss(self, cs, ps, cpr=None, ppr=None):
        """
        Builds both strangle and straddle
        """
        try:
            st = self.ST
            nd = self.ND
            expd = self.ED
            print("Building position", end=",")
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
            spt = spot[["SYMBOL", "CLOSE"]].rename(columns={"CLOSE": "SPOT"})
            df = spt.join([fnocs, fnops], how="outer")
            # call starting price
            if cpr is not None:
                df["CALL_CLOSE"].iat[0] = cpr
            csp = df.iloc[0]["CALL_CLOSE"]
            # put starting price
            if ppr is not None:
                df["PUT_CLOSE"].iat[0] = ppr
            psp = df.iloc[0]["PUT_CLOSE"]
            # total premium
            tp = csp + psp
            df = df.assign(TP=tp)
            df = df.assign(ITP=tp)
            df = df.assign(PNL=tp - df[["CALL_CLOSE", "PUT_CLOSE"]].sum(axis=1))
            df = df.assign(ED=expd)
            df = df.assign(ADN=0)
            df = self.calculate_pnl(df)
            return df[POSITION_COLUMNS]
        except Exception as e:
            print_exception(e)
            return None

    def build_ss_by_price(self, price):
        """
        Builds both strangle and straddle
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
            return self.build_ss(cs, ps)
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
            ed = nd
        else:
            ed = self.ED
        try:
            snd = st + timedelta(days=5)
            df = self.db.get_all_strike_data(st, snd, ed)
            # Get the first group only
            stt = df["TIMESTAMP"].unique()[0]
            df = df.query("TIMESTAMP==@stt and OPEN_INT>0 and CHG_IN_OI!=0")
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
            ).reset_index(drop=True)
            # Difference between call and put price
            opm = opm.assign(DIF=(opm["CLOSE_C"] - opm["CLOSE_P"]).abs())
            # Average price
            opm = opm.assign(PR=opm[["CLOSE_P", "CLOSE_C"]].mean(axis=1))
            # Starting day may not be a trading day, hence do this.
            idx = opm["DIF"].reset_index(drop=True).idxmin()
            atm = opm[["STRIKE_PR", "CLOSE_P", "CLOSE_C", "PR", "DIF"]].iloc[idx]
            print(f"ATM strike price {atm.STRIKE_PR:.0f}")
            return atm
        except Exception as e:
            print("Error getting atm strike ", end="-")
            print(f" st='{st:%Y-%m-%d}'", end=",")
            print(f" nd='{nd:%Y-%m-%d}'", end=",")
            print(f" ed='{ed:%Y-%m-%d}'", end=",")
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
            f"{self.symbol}_SSG_{num_expiry}"
            f"_price_{price}"
            f"_{self.SSAF}"
            f"_{datetime.now():%Y-%b-%d_%H-%M-%S}.xlsx"
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
                sdf = self.build_ss_by_price(price)
                rdf = self.repair_strangle(sdf, price, 1)
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
        sdf = self.build_ss_by_price(price)
        rdf = self.repair_strangle(sdf, price, 1)
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
        sdf = self.build_ss(conf["CS"], conf["PS"], conf["CPR"], conf["PPR"])
        if (conf["CPR"] is not None) and (conf["PPR"] is not None):
            price = (conf["CPR"] + conf["PPR"]) / 2
        else:
            price = sdf["TP"].iloc[0] / 2
        rdf = self.repair_strangle(sdf, price, 1)
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

    def e2e_SSR(self, num_expiry, exp_month=1):
        """
        Expiry to expiry straddle creator
        
        Parameters
        ----------
        num_expiry : int
            Number of expirys to process
        """
        expd = self.get_expiry_df(num_expiry, exp_month)
        #
        file_name = (
            f"{self.symbol}_STR_{num_expiry}"
            f"_{self.SSAF:.2f}"
            f"_{self.NOAD}"
            f"_{datetime.now():%Y-%b-%d_%H-%M-%S}.xlsx"
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
                atm = self.get_atm_strike()
                sdf = self.build_ss(atm.STRIKE_PR, atm.STRIKE_PR)
                rdf = self.repair_straddle(sdf, 1)
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

    def e2e_SSR_SE_custom(self, conf):
        """ Creates straddle for single expiry day
        between given start and end days """
        self.ST = conf["ST"]
        self.ND = conf["ND"]
        self.ED = conf["ED"]
        sdf = self.build_ss(conf["STRIKE"], conf["STRIKE"], conf["CPR"], conf["PPR"])
        rdf = self.repair_straddle(sdf, 1)
        file_name = (
            f"{self.symbol}_SSR_custom_"
            f"{self.ED:%Y-%b-%d}"
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

    def e2e_SSR_SE(self, st, nd, ed):
        """ Creates straddle for single expiry day
        between given start and end days """
        self.ST = st
        self.ND = nd
        self.ED = ed
        atm = self.get_atm_strike()
        sdf = self.build_ss(atm.STRIKE_PR, atm.STRIKE_PR)
        # Do not adjust before number of days
        self.ST = sdf.index[self.NOAD]
        rdf = self.repair_straddle(sdf, 1)
        file_name = (
            f"{self.symbol}_SSG_"
            f"{self.ED:%Y-%b-%d}"
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
