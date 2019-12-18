from src.obt import obt
bt = obt()
bt.symbol = 'nifty'
#1
bt.ST = "2019-5-31"
bt.ND = "2019-8-29"
bt.ED = "2019-8-29"
df = bt.e2e_SSG_SE_by_price("2019-5-31", "2019-8-29", "2019-8-29", 100)
#2
df = bt.e2e_SSR_SE("2019-03-01", "2019-03-28", "2019-03-28")