from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger
from datetime import datetime as dt
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from omspy_brokers.bypass import Bypass
from connection_manager import ConnectionManager
from oc_builder import Oc_builder
import pandas as pd

import json
import asyncio
import re
from copy import deepcopy
import inspect

# points to add/sub to ltp for limit orders
buff = -2

# toolkit modules
u = Utilities()
f = Fileutils()
logging = Logger(20, 'app.log')


try:
    # init broker object
    tok_file = './../../../confid/bypass.tok'
    lst_credential = f.get_lst_fm_yml('../../../confid/bypass.yaml')
    if f.is_file_not_2day(tok_file) is False:
        dct_tkns = {}
        logging.info('token file modified today')
        with open(tok_file, 'r') as tf:
            enctoken = tf.read()
        if enctoken:
            dct_tkns['enctoken'] = enctoken
            dct_tkns['userid'] = lst_credential.get('userid')
            lst_credential = dct_tkns
    bypass = Bypass(lst_credential)
    with open(tok_file, 'w') as tf:
        tf.write(bypass.kite.enctoken)
except Exception as e:
    logging.warning(f"unable to create broker object {e}")

try:
    sym = 'NIFTY'
    # validate option build dict files
    BUILD_PATH = "strikes/"
    lst_build_files = f.get_files_with_extn('yaml', BUILD_PATH)
    oc = Oc_builder(lst_build_files, BUILD_PATH)
    oc.set_symbol_dict(sym)
    dct_build = oc.dct_build
except Exception as e:
    logging.error(f'building {e}')

# get ltp of the underlying to get the ATM
ulying = bypass.ltp(dct_build['base_script'])
base_ltp = ulying[dct_build['base_script']]["last_price"]

# more settings for builder
atm = oc.get_atm_strike(base_ltp)
exchsym = oc.get_syms_fm_atm(atm)
buy_pipe, sell_pipe, BUY_OPEN, SELL_OPEN = [], [], [], []


def get_quotes():
    try:
        global base_ltp
        exchsym.append(dct_build['base_script'])
        resp = bypass.ltp(exchsym)
        base_ltp = resp[dct_build['base_script']]["last_price"]
        del resp[dct_build['base_script']]
        row = {}
        option_types_n_strikes = [
            (tradingsymbol, "CALL", re.search(
                r"(\d{5})+?CE?", tradingsymbol).group(0)[:-2])
            if tradingsymbol.endswith("CE")
            else (tradingsymbol, "PUT", re.search(r"(\d{5})+?PE?", tradingsymbol).group(0)[:-2])
            for tradingsymbol in [key.split(":")[-1] for key in resp.keys()]
        ]
        [
            row.update(
                {
                    strike_price: {
                        "call": {
                            tradingsymbol: resp[f"NFO:{tradingsymbol}"]["last_price"]
                        }
                    }
                }
            )
            for tradingsymbol, option_type, strike_price in option_types_n_strikes
            if option_type == "CALL"
        ]
        [
            row[strike_price].update(
                {"put": {
                    tradingsymbol: resp[f"NFO:{tradingsymbol}"]["last_price"]}}
            )
            for tradingsymbol, option_type, strike_price in option_types_n_strikes
            if option_type == "PUT"
        ]
    except Exception as b:
        logging.warning(f"exception {b}")
    else:
        return row


def get_ltp_fm_chain(tsym: str, quotes: List):
    if tsym.endswith('CE'):
        strike = re.search(r"(\d{5})+?CE?", tsym).group(0)[:-2]
        ltp = quotes.get(strike).get('call').get(tsym)
        return ltp
    elif tsym.endswith('PE'):
        strike = re.search(r"(\d{5})+?PE?", tsym).group(0)[:-2]
        ltp = quotes.get(strike).get('put').get(tsym)
        return ltp
    else:
        logging.info("tsym neither call nor put")

# orders helper


def upordn(old_sym: str, mv_by: int):
    if old_sym.endswith('CE'):
        old_strk = re.search(r"(\d{5})+?CE?", old_sym).group(0)[:-2]
    elif old_sym.endswith('PE'):
        old_strk = re.search(r"(\d{5})+?PE?", old_sym).group(0)[:-2]
    new_strk = int(old_strk) + (mv_by * dct_build['addsub'])
    new_sym = old_sym.replace(old_strk, str(new_strk))
    return new_sym


def order_place(order: List):
    try:
        order_id = bypass.order_place(**order)
        if isinstance(order_id, str):
            return order_id
        else:
            logging.warning(f'no order id {order_id}')
    except Exception as e:
        logging.warning(f'order place {e}')


def get_orders():
    order_book = bypass.orders
    data = {}
    if any(order_book):
        for page in order_book:
            order_id = page['order_id']
            data[order_id] = page
    return data


def get_positions():
    pos = bypass.positions
    day = {}
    if any(pos):
        for d in range(len(pos)):
            day[pos[d]['tradingsymbol']] = pos[d]
    return day


def modify_orders(lst, side, quotes):
    try:
        book = get_orders()
        if any(book):
            for o in lst:
                status = book[o]['status']
                if status == 'REJECTED' or status == 'CANCELLED':
                    lst.pop()
                    logging.warning(f'{status} {o}')
                elif status == 'COMPLETE':
                    lst.pop()
                elif status == 'WAITING':
                    logging.info(f'{book[o]["order_id"]} is {status}')
                elif status == 'OPEN' or status == 'PENDING':
                    ltp = get_ltp_fm_chain(book[o]['tradingsymbol'], quotes)
                    ltp += (buff * side)
                    logging.info(f'modifying {status} {o} {ltp}')
                    bypass.order_modify(
                        price=ltp, order_id=book[o]['order_id'])
            return lst
        return []
    except Exception as e:
        logging.warning(f'modify orders {e}')


def do_orders(quotes):
    global buy_pipe, sell_pipe, BUY_OPEN, SELL_OPEN
    # are broker buy orders open in ?
    if BUY_OPEN:
        lst_cp = deepcopy(BUY_OPEN)
        BUY_OPEN = modify_orders(lst_cp, 1, quotes)
        return 1
    elif buy_pipe:
        for o in buy_pipe:
            ltp = get_ltp_fm_chain(o['tradingsymbol'], quotes)
            o['price'] = ltp + (1*buff)
            order_id = order_place(o)
            if order_id:
                BUY_OPEN.append(order_id)
                logging.info(f'buy order {order_id} placed')
            else:
                logging.warn('buy order failed')
            buy_pipe.pop()
        return 2
    elif SELL_OPEN:
        lst_cp = deepcopy(SELL_OPEN)
        SELL_OPEN = modify_orders(lst_cp, -1, quotes)
        return -1
    elif sell_pipe:
        for o in sell_pipe:
            ltp = get_ltp_fm_chain(o['tradingsymbol'], quotes)
            o['price'] = ltp - (1*buff)
            order_id = order_place(o)
            if order_id:
                SELL_OPEN.append(order_id)
                logging.info(f'sell order {order_id} placed')
            else:
                logging.warn(f'sell order {o} failed')
            sell_pipe.pop()
        return -2


ws_cm = ConnectionManager()
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
tmp = Jinja2Templates(directory='templates')


async def slp_til_next_sec():
    t = dt.now()
    interval = t.microsecond / 1000000
    await asyncio.sleep(interval)
    return interval


@app.post("/orders")
async def post_orders(
    oqty: Optional[List[str]] = Form(),
    inp: str = Form(), do: str = Form(),
    tsym: List[str] = Form(),
    odir: Optional[List[str]] = Form(),
    chk: Optional[List[str]] = Form()
):
    global buy_pipe, sell_pipe

    if (do == 'up') or (do == 'dn'):
        if len(chk) > 0 and int(inp) > 0:
            pos = get_positions()
            for sym in chk:
                if sym in pos[0]:
                    o = {}
                    o['exchange'] = pos[sym]['exchange']
                    o['order_type'] = 'LIMIT'
                    o['product'] = pos[sym]['product']
                    o['quantity'] = abs(pos[sym]['quantity'])
                    c = deepcopy(o)
                    o['tradingsymbol'] = pos[sym]['tradingsymbol']
                    mv_by = int(inp) if do == 'up' else int(inp) * -1
                    logging.info(f'mv_by  {mv_by}')
                    new_sym = upordn(pos[sym]['tradingsymbol'], mv_by)
                    c['tradingsymbol'] = new_sym
                    c['transaction_type'] = pos[sym]['transaction_type']
                    if pos[sym]['transaction_type'] == 'SELL':
                        o['transaction_type'] = 'BUY'
                        buy_pipe.append(o)
                        sell_pipe.append(c)
                    else:
                        o['transaction_type'] = 'SELL'
                        sell_pipe.append(o)
                        buy_pipe.append(c)

    if do == 'send':
        for k, quantity in enumerate(oqty):
            if quantity != "":
                o = {}
                o['exchange'] = dct_build['opt_exch']
                o['transaction_type'] = odir[k]
                o['order_type'] = 'LIMIT'
                o['product'] = 'MIS'
                o['quantity'] = quantity
                o['tradingsymbol'] = tsym[k]
                if odir[k] == 'BUY':
                    buy_pipe.append(o)
                else:
                    sell_pipe.append(o)

    return {'buy orders': buy_pipe, 'sell orders': sell_pipe}
    # return  { 'oqty': oqty, 'do': do, 'tsym': tsym,
    #         'odir': odir, 'chk': chk }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_cm.connect(websocket)
    try:
        data = {}
        while True:
            interval = await slp_til_next_sec()
            positions = get_positions()
            data['positions'] = positions
            interval = await slp_til_next_sec()
            quotes = get_quotes()
            do_orders(quotes)
            data['quotes'] = quotes
            atm = oc.get_atm_strike(base_ltp)
            data['time'] = {'slept': interval,
                            'tsym': dct_build['base_script'],
                            'atm': atm,
                            'ltp': base_ltp}
            await ws_cm.send_personal_message(json.dumps(data), websocket)
    except WebSocketDisconnect:
        ws_cm.disconnect(websocket)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    ctx = {"request": request, "title": inspect.stack()[0][3]}
    return tmp.TemplateResponse("index.html", ctx)


@app.get("/orderbook", response_class=HTMLResponse)
async def orderbook(request: Request):
    bk = bypass.orders
    if not bk:
        bk = [{'message': 'no data'}]
    df = pd.DataFrame(
        data=bk,
        columns=bk[0].keys()
    )
    ctx = {"request": request, "title": inspect.stack()[0][3],
           "data": df.to_html()}
    return tmp.TemplateResponse("table.html", ctx)


@app.get("/positionbook", response_class=HTMLResponse)
async def positionbook(request: Request):
    bk = bypass.positions
    if not bk:
        bk = [{'message': 'no data'}]
    df = pd.DataFrame(
        data=bk,
        columns=bk[0].keys()
    )
    ctx = {"request": request, "title": inspect.stack()[0][3],
           "data": df.to_html()}
    return tmp.TemplateResponse("table.html", ctx)


@app.get("/tradebook", response_class=HTMLResponse)
async def tradebook(request: Request):
    bk = bypass.trades
    if not bk:
        bk = [{'message': 'no data'}]
    df = pd.DataFrame(
        data=bk,
        columns=bk[0].keys()
    )
    ctx = {"request": request, "title": inspect.stack()[0][3],
           "data": df.to_html()}
    return tmp.TemplateResponse("table.html", ctx)
