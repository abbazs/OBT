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
from src.excel_util import (
    add_style,
    create_summary_sheet,
    create_worksheet,
    create_inputsheet,
)
from src.hdf5db import hdf5db
from src.log import print_exception, start_logger


class obt(object):
    def __init__(self):
        try:
            start_logger()
            self.db = hdf5db.from_path(r"/home/abbas/work/github/hdf5db/indexdb.hdf")
            self.spot = None
            """ Symbol to be tested """
            self._SYMBOL = None
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
            self._MITR = None
            """ Current iteration number """
            self._CITR = None
            """ Strangle or straddle adjustment factor """
            self._SSAF = None
            """ No adjustment if the number of days to expiry is less than NOAD """
            self._NOAD = 5
            """ Which month, current, next or far? """
            self._MONTH = None
            """ Number of days before expiry """
            self._NDAYS = None
            """ Number of expirys to process """
            self._NDAYS = None
            """ Output file name """
            self._OPFN = None
            """ ATM for the given period """
            self.ATM = None
            """ STRIKE INCREMENT INTERVAL """
            self._SINCR = None
        except Exception as e:
            print_exception(e)

    @property
    def OUTPUT(self):
        if self.ODF is None:
            raise Exception("Output dataframe not generated.")
        else:
            return len(self.ODF)

    @property
    def SSAF(self):
        """ Adjustment factor to be of straddle or strangle """
        if self._SSAF is None:
            raise Exception("Strangle or straddle adjustment factor not set.")
        else:
            return self._SSAF

    @SSAF.setter
    def SSAF(self, value):
        self._SSAF = value

    @property
    def MITR(self):
        """Number or iterations to be processed"""
        if self._MITR is None:
            raise Exception("MITR is None - Max repair iterations is not set.")
        else:
            return self._MITR

    @MITR.setter
    def MITR(self, value):
        self._MITR = value

    @property
    def CITR(self):
        """ Current iteration number """
        if self._CITR is None:
            raise Exception("CITR is None - Current iteration is not set.")
        else:
            return self._CITR

    @CITR.setter
    def CITR(self, value):
        self._CITR = value

    @property
    def NOAD(self):
        """ No adjustment if the number of days to expiry is less than """
        if self._NOAD is None:
            raise Exception(
                "NOAD is None - No adjustment after number of days not set."
            )
        else:
            return self._NOAD

    @NOAD.setter
    def NOAD(self, value):
        self._NOAD = value

    @property
    def MONTH(self):
        """ Which month, current, next or far? """
        if self._MONTH is None:
            raise Exception("MONTH is None - Month to process has not been set.")
        else:
            return self._MONTH

    @MONTH.setter
    def MONTH(self, value):
        self._MONTH = value

    @property
    def NDAYS(self):
        """ Number of days to ahead of expiry to process """
        if self._NDAYS is None:
            raise Exception(
                "NDAYS is None - Number of days to ahead of expiry to process has not been set."
            )
        else:
            return self._NDAYS

    @NDAYS.setter
    def NDAYS(self, value):
        self._NDAYS = value

    @property
    def SINCR(self):
        """ Number of days to ahead of expiry to process """
        if self._SINCR is None:
            raise Exception("SINCR is None - Strike increment interval is none.")
        else:
            return self._SINCR

    @SINCR.setter
    def SINCR(self, value):
        self._SINCR = value

    @property
    def NEXP(self):
        """ Number of expirys to process """
        if self._NEXP is None:
            raise Exception(
                "NEXP is None - Number of expirys to process has not been set."
            )
        else:
            return self._NEXP

    @NEXP.setter
    def NEXP(self, value):
        self._NEXP = value

    @property
    def OPFN(self):
        """ Output file name """
        if self._OPFN is None:
            raise Exception("OPFN is None - Output file name has not been set.")
        else:
            return self._OPFN

    @OPFN.setter
    def OPFN(self, value):
        self._OPFN = value

    @property
    def SYMBOL(self):
        """symbol to be processed"""
        if self._SYMBOL is None:
            raise Exception("SYMBOL is None - Symbol is not yet set.")
        else:
            return self._SYMBOL

    @SYMBOL.setter
    def SYMBOL(self, value):
        self._SYMBOL = value.upper()
        self.db.set_symbol_instrument(self.SYMBOL, "OPTIDX")

    @property
    def ST(self):
        """ Start Date """
        if self._ST is None:
            raise Exception("ST is None - Start date has not been set.")
        else:
            return self._ST

    @ST.setter
    def ST(self, value):
        self._ST = process_date(value)

    @property
    def ND(self):
        """ End Date """
        if self._ND is None:
            raise Exception("ND is None - End date has not been set.")
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
        # When ever ED is being set reset
        # the value of CITR to 1
        self.CITR = 1
        # Reset ATM to None
        self.ATM = None

    def save_inputs_to_excel(self, ewb):
        df = pd.DataFrame(
            {
                "SYMBOL": self.SYMBOL,
                "MONTH": self._MONTH,
                "NDAYS": self._NDAYS,
                "NO_ADJUSTMENT_DAYS": self.NOAD,
                "MAX_NUMBER_OF_ADJUSTMENTS": self.MITR,
                "ADJUSTMENT_FACTOR": self.SSAF,
            },
            index=[0],
        )
        create_inputsheet(ewb, df.T)
        self.ODF.to_excel(excel_writer=ewb, sheet_name="INPUTS", startrow=0, startcol=4)

    def get_expiry_df(self, num_expiry):
        """
        Gets expiry dates for number of expirys required.
        -------------------------------------------------
        Parameters
        ----------
        num_expiry -> (int) number of expirys required
        -------------------------------------------------
        Returns
        -------
        retun -> (pandas.DataFrame) a dataframe containing start date, end date and expiry dates
        """
        # Get expiry dates
        # ST - START DATE
        # ED - EXPIRY DATE
        # ND - END DATE
        expd = self.db.get_past_n_expiry_dates(num_expiry, "FUTIDX")
        expd = expd.rename(columns={"EXPIRY_DT": "ED"})
        expd = expd.assign(ST=expd.shift(self.MONTH) + pd.Timedelta("1Day"))
        expd = expd.assign(ND=expd["ED"])
        expd = expd.dropna().reset_index(drop=True)
        return expd

    def get_expiry_df_before_num_days(self, num_expiry):
        """
        Gets expiry dates for number of expirys required.
        Starting day is set based of number of days before 
        expiry day
        -------------------------------------------------
        Parameters
        ----------
        num_expiry -> (int) number of expirys required
        -------------------------------------------------
        Returns
        -------
        retun -> (pandas.DataFrame) a dataframe containing start date, end date and expiry dates
        """
        # Get expiry dates
        # ST - START DATE
        # ED - EXPIRY DATE
        # ND - END DATE
        expd = self.db.get_past_n_expiry_dates(num_expiry, "FUTIDX")
        expd = expd.rename(columns={"EXPIRY_DT": "ED"})
        expd = expd.assign(ST=expd.ED - pd.Timedelta(self.NDAYS, "D"))
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

    def print_inputs(self):
        print(f" -ST={self.ST:%Y-%m-%d}", end=",")
        print(f" -ND={self.ND:%Y-%m-%d}", end=",")
        print(f" -ED={self.ED:%Y-%m-%d}", end=",")

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
        try:
            df = df.assign(TP=tp)
            df = df.assign(PNL=tp - df[["CALL_CLOSE", "PUT_CLOSE"]].sum(axis=1))
            df = df.assign(UBK=df.CS + tp)
            df = df.assign(LBK=df.PS - tp)
            df = df.assign(WIDTH=df.UBK - df.LBK)
            df = df.assign(CBK=df.CS + (tp * self.SSAF))
            df = df.assign(PBK=df.PS - (tp * self.SSAF))
            df = df.assign(CBS=(df.CBK / self.SINCR).apply(np.floor) * self.SINCR)
            df = df.assign(PBS=(df.PBK / self.SINCR).apply(np.ceil) * self.SINCR)
            df = df.assign(UW=df.CBK - df.FUTURE)
            df = df.assign(LW=df.FUTURE - df.PBK)
            df = df.assign(WR=df.UW / df.LW)
            return df
        except Exception as e:
            print_exception(e)
            return None

    def check_adjustment_required(self, df):
        """ Checks if adjustment is required for position
        """
        print(f"Repair iteraion ({self.CITR}) : date {self.ST:%Y-%m-%d}")
        if self.CITR > self.MITR:
            print(f"Stopping repair iteration since max iteration done...")
            return False
        # Do not adjust if last adjustment is less than NOAD
        adns = df[: self.ST]["ADN"].unique()
        adn = adns[-1]
        adnl = len(df[: self.ST].query("ADN==@adn"))
        if adnl <= self.NOAD:
            if len(df[self.ST :]) > self.NOAD:
                self.ST = df[self.ST :].index[self.NOAD]
            else:
                print(f"Position is in no adjustment period.")
                return False
        # dfloc
        sdf = df[self.ST :]
        dfs = sdf.query("ATM>=@sdf.CBS.iloc[0] or ATM<@sdf.PBS.iloc[0]")
        if len(dfs) == 0:
            print(f"Not adjusting any further position in control...")
            return False
        else:
            dfii = dfs.iloc[0]
            dte = self.ED - dfii.name
            if dte.days <= self.NOAD:
                print(
                    f"Not adjusting any further days to expiry is less than ({dte.days})..."
                )
                return False
            else:
                return dfii

    def repair_position_by_price(self, df, price):
        """ Repairs a strangle position
        Which ever leg is in profit, more than 50% of price
        close it and move to the next strike available at
        the price.
        Do the repair only when any one of the leg is in loss.
        """
        dfii = self.check_adjustment_required(df)
        if dfii is False:
            return df
        print("Need to adjust")
        dfk = df[self.ST :].iloc[0]
        self.ST = dfii.name
        adp_pnl = dfk.PUT_CLOSE - dfii.PUT_CLOSE
        adc_pnl = dfk.CALL_CLOSE - dfii.CALL_CLOSE
        print(f"Adjustment profit {adc_pnl:.2f}")
        print(f"Adjustment loss {adp_pnl:.2f}")
        dfc = self.db.get_all_strike_data(dfii.name, dfii.name, dfii.ED)
        # Adjust call
        cs = self.get_strike_price(dfc, "CE", price)
        fno = self.db.get_strike_price(dfii.name, dfii.ED, dfii.ED, "CE", cs)
        fno = self.rename_call_columns(fno)
        df.loc[fno.index, ["CALL_CLOSE", "COI", "CCOI", "CS"]] = fno
        # Adjust put
        ps = self.get_strike_price(dfc, "PE", price)
        fno = self.db.get_strike_price(dfii.name, dfii.ED, dfii.ED, "PE", ps)
        fno = self.rename_put_columns(fno)
        df.loc[fno.index, ["PUT_CLOSE", "POI", "PCOI", "PS"]] = fno
        # calculate new target profit
        tpl = df.loc[fno.index, ["CALL_CLOSE", "PUT_CLOSE"]].iloc[0]
        tp = tpl.sum() + adp_pnl + adc_pnl
        #
        dfr = self.calculate_repaired_pnl(df.loc[fno.index], tp)
        df.loc[fno.index] = dfr
        df.loc[fno.index, "ADN"] = self.CITR
        self.CITR += 1
        return self.repair_position_by_price(df, price)

    def repair_position_by_straddle(self, df):
        """ Repairs a straddle position
        """
        dfii = self.check_adjustment_required(df)
        if dfii is False:
            return df
        dfk = df[self.ST :].iloc[0]
        self.ST = dfii.name
        atm = self.get_atm_strike()
        # Adjust Call
        fno = self.db.get_strike_price(dfii.name, dfii.ED, dfii.ED, "CE", atm)
        fno = self.rename_call_columns(fno)
        df.loc[fno.index, ["CALL_CLOSE", "COI", "CCOI", "CS"]] = fno
        # Adjust Put
        fno = self.db.get_strike_price(dfii.name, dfii.ED, dfii.ED, "PE", atm)
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
        df.loc[fno.index, "ADN"] = self.CITR
        self.CITR += 1
        return self.repair_position_by_straddle(df)

    def build_ss(self, cs, ps, cpr=None, ppr=None):
        """
        Builds both strangle and straddle
        """
        try:
            self.CITR = 1
            st = self.ST
            nd = self.ND
            expd = self.ED
            print("Building position", end=",")
            self.print_inputs()
            print(f" Call : {cs}", end=",")
            print(f" Put : {ps}", end=",")
            print(f" CallPr : {cpr}", end=",")
            print(f" PutPr : {ppr}")
            spot = self.db.get_index_data_between_dates(st, nd)
            vix = self.db.get_vix_data_between_dates(st, nd)
            fut = self.db.get_future_price(st, nd, expd)
            fnocs = self.db.get_strike_price(st, nd, expd, "CE", cs)
            fnocs = self.rename_call_columns(fnocs)
            fnops = self.db.get_strike_price(st, nd, expd, "PE", ps)
            fnops = self.rename_put_columns(fnops)
            spt = spot[["SYMBOL", "CLOSE"]].rename(columns={"CLOSE": "SPOT"})
            vx = vix[["CLOSE"]].rename(columns={"CLOSE": "VIX"})
            df = spt.join([vx, fut, fnocs, fnops], how="outer")
            df.loc[df.FUTURE.isna(), "FUTURE"] = df.SPOT
            atm = self.get_atm_strike()
            df = df.assign(ATM=self.ATM[self.ST :])
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
            df = df.assign(DTE=(df.ED - df.index).dt.days)
            df = df.assign(DTER=(df.ED - df.index[::-1]).dt.days)
            df = self.calculate_pnl(df)
            # Sometimes the start date in data frame will not be same as
            # the given start date
            self.ST = df.index[0]
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
            self.print_inputs()
            print(f" price={price}")
            print_exception(e)
            return None

    def process_atm(self, df):
        try:
            opg = df.query("OPEN_INT>0 and CHG_IN_OI!=0").groupby("OPTION_TYP")
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
            atm = atm.STRIKE_PR
            return atm
        except:
            print(f"Error getting atm for {df.name:%Y-%m-%d}")
            return None

    def get_atm_strike(self):
        """
        Retruns ATM strike
        """
        try:
            if self.ATM is None:
                df = self.db.get_all_strike_data(self.ST, self.ND, self.ED)
                self.ATM = df.groupby("TIMESTAMP").apply(self.process_atm)

            atml = self.ATM[self.ST :]
            atmf = atml[atml > 0]
            atm = atmf.iloc[0]
            self.ST = atmf.index[0]
            return atm
        except Exception as e:
            print("Error getting atm strike ", end="-")
            self.print_inputs()
            print_exception(e)
            return None

    def ssg(self, expd, price):
        full_file_name = Path(self.out_path).joinpath(self.OPFN)
        ewb = pd.ExcelWriter(full_file_name, engine="openpyxl")
        add_style(ewb)
        smry = []
        for x in expd.itertuples():
            try:
                self.ST = x.ST
                self.ND = x.ND
                self.ED = x.ED
                sdf = self.build_ss_by_price(price)
                rdf = self.repair_position_by_price(sdf, price)
                create_worksheet(ewb, rdf, f"{x.ED:%Y-%m-%d}", self.OPFN, index=x.Index)
                smry.append(sdf.iloc[-1])
            except Exception as e:
                print_exception(e)
                print("Error processing last...")
        # save work book
        summary = pd.DataFrame(smry)
        create_summary_sheet(ewb, summary, self.OPFN)
        self.ODF = summary.resample("Y").sum()[["APNL", "PNL"]]
        self.save_inputs_to_excel(ewb)
        ewb.book._sheets.reverse()
        ewb.save()
        print(f"Saved file {full_file_name}")

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
        expd = self.get_expiry_df(num_expiry)
        #
        self.OPFN = (
            f"{self.SYMBOL}_SSG_{self.NEXP}"
            f"_{self.SSAF:.2f}"
            f"_{self.MONTH}"
            f"_{self.NOAD}"
            f"_{price}"
            f"_{datetime.now():%Y-%b-%d_%H-%M-%S}.xlsx"
        )
        self.ssg(expd, price)

    def SSG_ndays_before_by_price(self, num_expiry, price):
        """
        Expiry to ndays before straddle creator
        
        Parameters
        ----------
        num_expiry : int
            Number of expirys to process
        price : float
            Price to create the strangle
        """
        expd = self.get_expiry_df_before_num_days(num_expiry)
        self.OPFN = (
            f"{self.SYMBOL}_SSG_{self.NEXP}"
            f"_{self.SSAF:.2f}"
            f"_{self.NDAYS}"
            f"_{self.NOAD}"
            f"_{price}"
            f"_{datetime.now():%Y-%b-%d_%H-%M-%S}.xlsx"
        )
        self.ssg(expd, price)

    def e2e_SSG_SE_by_price(self, st, nd, ed, price):
        """ Creates strangle for single expiry day
        between given start and end days """
        self.ST = st
        self.ND = nd
        self.ED = ed
        sdf = self.build_ss_by_price(price)
        rdf = self.repair_position_by_price(sdf, price)
        file_name = (
            f"{self.SYMBOL}_SSG_"
            f"{self.ED:%Y-%b-%d}_"
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
        between given start and end days with
        price details of entry of strikes"""
        self.ST = conf["ST"]
        self.ND = conf["ND"]
        self.ED = conf["ED"]
        sdf = self.build_ss(conf["CS"], conf["PS"], conf["CPR"], conf["PPR"])
        if (conf["CPR"] is not None) and (conf["PPR"] is not None):
            price = (conf["CPR"] + conf["PPR"]) / 2
        else:
            price = sdf["TP"].iloc[0] / 2
        rdf = self.repair_position_by_price(sdf, price)
        file_name = (
            f"{self.SYMBOL}_SSG_custom_"
            f"{self.ED:%Y-%b-%d}_"
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

    def ssr(self, expd):
        full_file_name = Path(self.out_path).joinpath(self.OPFN)
        ewb = pd.ExcelWriter(full_file_name, engine="openpyxl")
        add_style(ewb)
        smry = []
        for x in expd.itertuples():
            try:
                self.ST = x.ST
                self.ND = x.ND
                self.ED = x.ED
                atm = self.get_atm_strike()
                sdf = self.build_ss(atm, atm)
                rdf = self.repair_position_by_straddle(sdf)
                create_worksheet(ewb, rdf, f"{x.ED:%Y-%m-%d}", self.OPFN, index=x.Index)
                smry.append(sdf.iloc[-1])
            except Exception as e:
                print_exception(e)
                print("Error processing last...")
        # save work book
        summary = pd.DataFrame(smry)
        create_summary_sheet(ewb, summary, self.OPFN)
        self.ODF = summary.resample("Y").sum()[["APNL", "PNL"]]
        self.save_inputs_to_excel(ewb)
        ewb.book._sheets.reverse()
        ewb.save()
        print(f"Saved file {full_file_name}")

    def e2e_SSR(self, num_expiry):
        """
        Expiry to expiry straddle creator
        
        Parameters
        ----------
        num_expiry : int
            Number of expirys to process
        """
        expd = self.get_expiry_df(num_expiry)
        self.OPFN = (
            f"{self.SYMBOL}_SSR_{self.NEXP}"
            f"_{self.SSAF:.2f}"
            f"_{self.MONTH}"
            f"_{self.NOAD}"
            f"_{datetime.now():%Y-%b-%d_%H-%M-%S}.xlsx"
        )
        self.ssr(expd)

    def SSR_ndays_before(self, num_expiry):
        """
        Expiry to ndays before straddle creator
        
        Parameters
        ----------
        num_expiry : int
            Number of expirys to process
        """
        expd = self.get_expiry_df_before_num_days(num_expiry)
        self.OPFN = (
            f"{self.SYMBOL}_SSR_{self.NEXP}"
            f"_{self.SSAF:.2f}"
            f"_{self.NDAYS}"
            f"_{self.NOAD}"
            f"_{datetime.now():%Y-%b-%d_%H-%M-%S}.xlsx"
        )
        self.ssr(expd)

    def e2e_SSR_SE_custom(self, conf):
        """ Creates straddle for single expiry day
        between given start and end days """
        self.ST = conf["ST"]
        self.ND = conf["ND"]
        self.ED = conf["ED"]
        self.SINCR = conf["SINCR"]
        sdf = self.build_ss(conf["CS"], conf["PS"], conf["CPR"], conf["PPR"])
        rdf = self.repair_position_by_straddle(sdf)
        file_name = (
            f"{self.SYMBOL}_SSR_custom_"
            f"{self.ED:%Y-%b-%d}_"
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
        sdf = self.build_ss(atm, atm)
        # Do not adjust before number of days
        self.ST = sdf.index[self.NOAD]
        rdf = self.repair_position_by_straddle(sdf)
        file_name = (
            f"{self.SYMBOL}_SSRSE_"
            f"{self.ED:%Y-%b-%d}_"
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
