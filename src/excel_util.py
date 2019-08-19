import pathlib

import pandas as pd
from colour import Color
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference, Series, StockChart
from openpyxl.chart.axis import ChartLines, DateAxis
from openpyxl.chart.data_source import NumData, NumVal
from openpyxl.chart.label import DataLabel, DataLabelList
from openpyxl.chart.updown_bars import UpDownBars
from openpyxl.styles import Font, NamedStyle
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.hyperlink import Hyperlink, HyperlinkList

from src.log import print_exception


def create_worksheet(ew, df, name, file_name):
    df.to_excel(excel_writer=ew, sheet_name=name)
    ws = ew.book[name]
    cels = [f"A{x}" for x in range(2, len(df) + 3)]
    for cl in cels:
        ws[cl].style = "custom_datetime1"
    cels = [f"B{x}" for x in range(2, len(df) + 3)]
    for cl in cels:
        ws[cl].style = "custom_datetime1"
    ws.column_dimensions["A"].width = 11
    ws.column_dimensions["B"].width = 11
    hyp = f"{file_name}#'SUMMARY'!A1"
    ws["A1"].hyperlink = hyp
    ws["A1"].hyperlink.location = hyp.split("#")[1]
    ws["A1"].style = "custom_datetime"

def create_summary_sheet(ew, df, file_name):
    df.to_excel(excel_writer=ew, sheet_name="SUMMARY")
    ws = ew.book["SUMMARY"]
    disps = [f"{file_name}#'{x:%Y-%m-%d}'!A1" for x in df.ED]
    cels = [f"B{x}" for x in range(2, len(disps) + 3)]
    for cl, hyp in zip(cels, disps):
        ws[cl].hyperlink = hyp
        ws[cl].hyperlink.location = hyp.split("#")[1]
        ws[cl].style = "custom_datetime"
    cels = [f"A{x}" for x in range(2, len(disps) + 3)]
    for cl in cels:
        ws[cl].style = "custom_datetime1"
    ws.column_dimensions["A"].width = 11
    ws.column_dimensions["B"].width = 11


def add_style(ew):
    ns = NamedStyle(name="custom_datetime", number_format="YYYY-MM-DD")
    ns.font = Font(underline="single", color="0000FF")
    ew.book.add_named_style(ns)
    ns = NamedStyle(name="custom_datetime1", number_format="YYYY-MM-DD")
    ns.font = Font(color="0000FF")
    ew.book.add_named_style(ns)
