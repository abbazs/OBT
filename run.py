import json
import os

import click

from src.obt import obt


@click.group()
@click.option("-symbol", default="NIFTY")
@click.pass_context
def cli(ctx, symbol):
    """ Options back testing """
    ctx.obj["SYMBOL"] = symbol.upper()
    ob = obt()
    ob.symbol = symbol
    ctx.obj["OBT"] = ob


@cli.command(help="Back test strangle for number of expiries")
@click.pass_context
@click.option("-nexp", help="Number of expiries.", default=60)
@click.option(
    "-which_month", help="1 - current month, 2 - next month, 3 - far month", default=1
)
@click.option("-price", help="what price strangle needs to be created", default=50)
def stg(ctx, nexp, which_month, price):
    """ Run strangle """
    ctx.obj["NEXP"] = nexp
    ctx.obj["WM"] = which_month
    ctx.obj["PR"] = price
    print(ctx.obj)
    ob = ctx.obj["OBT"]
    ob.e2e_SSG_by_price(nexp, price, which_month)


@cli.command(
    help="Study strangle for a given start date, end date and expiry date and price"
)
@click.pass_context
@click.option("-ST", help="Start date", default=None)
@click.option("-ND", help="End date", default=None)
@click.option("-ED", help="Expiry date", default=None)
@click.option("-price", help="what price strangle needs to be created", default=50)
def sstg(ctx, ST, ND, ED, price):
    """ Run strangle """
    ctx.obj["ST"] = ST
    ctx.obj["ND"] = ND
    ctx.obj["ED"] = ED
    ctx.obj["PR"] = price
    print(ctx.obj)
    ob = ctx.obj["OBT"]
    ob.e2e_SSG_SE_by_price(ST, ND, ED, price)


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
    ob.e2e_SSR(nexp, month)


if __name__ == "__main__":
    cli(obj={})
