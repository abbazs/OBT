from src.obt import obt
bt = obt()
bt.symbol = 'nifty'
bt.ST = "2019-5-31"
bt.ND = "2019-8-29"
bt.ED = "2019-8-29"
df = bt.e2e_SSG_SE_by_price("2019-5-31", "2019-8-29", "2019-8-29", 100)