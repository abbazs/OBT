POSITION_COLUMNS = [
    "ED",
    "VIX",
    "SYMBOL",
    "SPOT",
    "FUTURE",
    "ATM",
    "PS",
    "CS",
    "PUT_CLOSE",
    "CALL_CLOSE",
    "TP", # TARGET PROFIT
    "CV", # CURRENT VALUE OF POSITION
    "APNL", # ACTUAL PROFIT AND LOSS
    "PNL", # PROFT AND LOSS
    "WIDTH", # ALLOWABLE SWING OF ATM
    "PBS",  # PUT STOP LOSS STRIKE
    "CBS",  # CALL STOP LOSS STRIKE
    "ITP",  # Initial target profit
    "ADN",  # Adjustment number
    "DTE",  # Days to expiry
    "DTER",  # Days to expiry in reverse
    # "MAXP", # Maximum profit achieved
]

CHART_COLUMNS = ["DTE", "PBK", "CBK", "PS", "CS", "SPOT", "FUTURE", "APNL", "PNL"]

UPPER_RANGE = "CBK"
LOWER_RANGE = "PBK"
