from src.obt import obt

if __name__ == '__main__':
    bt = obt()
    bt.symbol = 'nifty'
    bt.expiry2expiry_strangle(12*12, 125)