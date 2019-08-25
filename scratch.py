from src.obt import obt
bt = obt()
bt.symbol = 'nifty'
df = bt.e2e_SSG_SE_by_price("2018-10-26", "2018-11-29", "2018-11-29", 40)