from src.obt import obt
bt = obt()
bt.symbol = 'nifty'
df = bt.e2e_SSG_SE_by_price("2019-5-31", "2019-8-29", "2019-8-29", 100)