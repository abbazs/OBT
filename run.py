from src.obt import obt

if __name__ == '__main__':
    bt = obt()
    bt.symbol = 'nifty'
    bt.e2e_SSG_by_price(12*1, 40)