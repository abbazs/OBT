import json
import os

import click

from src.obt import obt


@click.group()
@click.option("-symbol", default="NIFTY")
@click.option("-mitr", help="Max number of times positon can be adjusted", default=5)
@click.option("-ssaf", help="Strangle or straddle adjustment factor", default=0.01)
@click.option("-noad", help="No adjustment if num days to expiry is less than noad", default=5)
@click.pass_context
def cli(ctx, symbol, mitr, ssaf, noad):
    """ Options back testing """
    ctx.obj["SYMBOL"] = symbol.upper()
    ob = obt()
    ob.symbol = symbol
    ob.MITR = mitr
    ob.SSAF = ssaf
    ob.NOAD = noad
    ctx.obj["OBT"] = ob


@cli.command(help="Back test strangle for number of expiries")
@click.pass_context
@click.option("-nexp", help="Number of expiries.", default=60)
@click.option(
    "-month", help="1 - current month, 2 - next month, 3 - far month", default=1
)
@click.option("-price", help="what price strangle needs to be created", default=50)
def stg(ctx, nexp, month, price):
    """ Run strangle """
    ctx.obj["NEXP"] = nexp
    ctx.obj["WM"] = month
    ctx.obj["PR"] = price
    print(ctx.obj)
    ob = ctx.obj["OBT"]
    ob.MONTH = month
    ob.e2e_SSG_by_price(nexp, price)


@cli.command(
    help="Study strangle for a given start date, end date and expiry date and price"
)
@click.pass_context
@click.option("-ST", help="Start date", default=None)
@click.option("-ND", help="End date", default=None)
@click.option("-ED", help="Expiry date", default=None)
@click.option("-price", help="what price strangle needs to be created", default=50)
def sstg(ctx, st, nd, ed, price):
    """ Run strangle """
    ctx.obj["ST"] = st
    ctx.obj["ND"] = nd
    ctx.obj["ED"] = ed
    ctx.obj["PR"] = price
    print(ctx.obj)
    ob = ctx.obj["OBT"]
    ob.e2e_SSG_SE_by_price(st, nd, ed, price)


@cli.command(
    help=(
        "Study strangle for a given start date, end date and expiry date and price "
        "- input in a json file"
    )
)
@click.pass_context
@click.option("-name", help="File name", default=None)
def sstgf(ctx, name):
    """ Run strangle """
    with open(name, "r") as f:
        conf = json.loads(f.read())
    ctx.obj["ST"] = conf["ST"]
    ctx.obj["ND"] = conf["ND"]
    ctx.obj["ED"] = conf["ED"]
    ctx.obj["PR"] = conf["PR"]
    print(ctx.obj)
    ob = ctx.obj["OBT"]
    ob.e2e_SSG_SE_by_price(conf["ST"], conf["ND"], conf["ED"], conf["PR"])


@cli.command(
    help=(
        "Study custom strangle for a given start date, end date, expiry date, "
        "call strike, put strike, call price, put price "
        "- input in a json file"
    )
)
@click.pass_context
@click.option("-name", help="File name", default=None)
def sstgc(ctx, name):
    """ Run strangle """
    with open(name, "r") as f:
        conf = json.loads(f.read())
    ctx.obj["ST"] = conf["ST"]
    ctx.obj["ND"] = conf["ND"]
    ctx.obj["ED"] = conf["ED"]
    ctx.obj["CS"] = conf["CS"]
    ctx.obj["PS"] = conf["PS"]
    ctx.obj["CPR"] = conf["CPR"]
    ctx.obj["PPR"] = conf["PPR"]
    print(ctx.obj)
    ob = ctx.obj["OBT"]
    ob.e2e_SSG_SE_custom(conf)


@cli.command(
    help=(
        "Study straddles for given number of expiry and month"
        " currnet month = 1 "
        " next month = 2 "
        " far month = 3 "
    )
)
@click.pass_context
@click.option("-nexp", help="Num expiries", default=12)
@click.option(
    "-month", help="1 - current month, 2 - next month, 3 - far month", default=1
)
def ssr(ctx, nexp, month):
    """ Run straddle """
    ob = ctx.obj["OBT"]
    ob.MONTH = month
    ob.e2e_SSR(nexp)


@cli.command(help="Study straddles for start, end and expiry days")
@click.pass_context
@click.option("-ST", help="Start date", default=None)
@click.option("-ND", help="End date", default=None)
@click.option("-ED", help="Expiry date", default=None)
def ssrs(ctx, st, nd, ed):
    """ Run straddle """
    ob = ctx.obj["OBT"]
    ob.e2e_SSR_SE(st, nd, ed)

@cli.command(
    help=(
        "Study custom straddle for a given start date, end date, expiry date, "
        "call strike, put strike, call price, put price "
        "- input in a json file"
    )
)
@click.pass_context
@click.option("-name", help="File name", default=None)
def ssrc(ctx, name):
    """ Run straddle """
    with open(name, "r") as f:
        conf = json.loads(f.read())
    ctx.obj["ST"] = conf["ST"]
    ctx.obj["ND"] = conf["ND"]
    ctx.obj["ED"] = conf["ED"]
    ctx.obj["CS"] = conf["CS"]
    ctx.obj["PS"] = conf["PS"]
    ctx.obj["CPR"] = conf["CPR"]
    ctx.obj["PPR"] = conf["PPR"]
    print(ctx.obj)
    ob = ctx.obj["OBT"]
    ob.e2e_SSR_SE_custom(conf)

if __name__ == "__main__":
    cli(obj={})