from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger
from toolkit.conman import ConnectionManager
from datetime import datetime as dt
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from omspy_brokers.bypass import Bypass
from oc_builder import Oc_builder
import pandas as pd
import uvicorn
import json
import asyncio
import re
from copy import deepcopy
import inspect
from time import sleep

# points to add/sub to ltp for limit orders
buff = -2
sym = 'NIFTY'

# toolkit modules
u = Utilities()
f = Fileutils()
logging = Logger(20, 'app.log')


try:
    # init broker object
    sec_dir = '../../../confid/'
    lst_c = f.get_lst_fm_yml(sec_dir + 'bypass.yaml')
    tokpath = sec_dir + lst_c['userid'] + '.txt'
    enctoken = None
    if f.is_file_not_2day(tokpath) is False:
        logging.info(
            f'token file modified today ... reading enctoken {enctoken}')
        """
        with open(tokpath, 'r') as tf:
            enctoken = (
                tf.read().decode('utf-8').strip()
                if isinstance(tf.read(), bytes)
                else tf.read().strip()
            )

        """
        with open(tokpath, 'r') as tf:
            enctoken = tf.read()
            if len(enctoken) < 5:
                enctoken = None
    logging.info(f'enctoken to broker {enctoken}')
    bypass = Bypass(lst_c['userid'],
                    lst_c['password'],
                    lst_c['totp'],
                    tokpath,
                    enctoken)
    if bypass.authenticate():
        if not enctoken:
            enctoken = bypass.kite.enctoken
            with open(tokpath, 'w') as tw:
                tw.write(enctoken)
except Exception as e:
    logging.error(f"unable to create broker object {e}")

try:
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
    """
    consumed by websocket for display
    """
    try:
        global base_ltp
        exchsym.append(dct_build['base_script'])
        row = {}
        resp = bypass.ltp(exchsym)
        if any(resp):
            base_ltp = resp[dct_build['base_script']]["last_price"]
            del resp[dct_build['base_script']]
            option_types_n_strikes = [
                (tradingsymbol, "CALL", re.search(
                    r"(\d{5})+?CE?", tradingsymbol).group(1)[:5])
                if tradingsymbol.endswith("CE")
                else (tradingsymbol, "PUT", re.search(
                    r"(\d{5})+?PE?", tradingsymbol).group(1)[:5])
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
        logging.error(f"exception {b}")
    else:
        return row


def get_ltp_fm_chain(tsym: str, quotes: List):
    if tsym.endswith('CE'):
        strike = re.search(r"(\d{5})+?CE?", tsym).group(1)[:5]
        ltp = quotes.get(strike).get('call').get(tsym)
        return ltp
    elif tsym.endswith('PE'):
        strike = re.search(r"(\d{5})+?PE?", tsym).group(1)[:5]
        ltp = quotes.get(strike).get('put').get(tsym)
        return ltp
    else:
        logging.info("tsym neither call nor put")


def _order_place(order: List):
    """
    orders helper
    """
    try:
        order_id = bypass.order_place(**order)
        if isinstance(order_id, str):
            return order_id
        else:
            logging.warning(f'no order id {order_id}')
    except Exception as e:
        logging.warning(f'order place {e}')


POSITIONS = {}


async def get_positions():
    global POSITIONS
    pos = bypass.positions
    data = {}
    if any(pos):
        for d in range(len(pos)):
            data[pos[d]['symbol']] = pos[d]
    POSITIONS = data
    return data


def _modify_orders(lst: List, dirtn: int, quotes: Dict):
    def get_orders():
        order_book = bypass.orders
        data = {}
        if any(order_book):
            for page in order_book:
                order_id = page['order_id']
                data[order_id] = page
        return data

    try:
        book = get_orders()
        if any(book):
            for o in lst:
                status = book[o]['status']
                logging.info(f'{book[o]["order_id"]} is {status}')
                if status == 'REJECTED' or status == 'CANCELLED' or status == 'COMPLETE':
                    lst.pop()
                    logging.INFO('removing')
                elif status == 'OPEN' or status == 'PENDING':
                    ltp = get_ltp_fm_chain(book[o]['symbol'], quotes)
                    ltp += (buff * dirtn)
                    logging.info(f'modifying price to {ltp}')
                    try:
                        bypass.order_modify(
                            price=ltp, order_id=book[o]['order_id'])
                    except Exception as e:
                        lst.pop()
                        logging.warning(f'modify orders {e}')
            return lst
        return []
    except Exception as e:
        logging.warning(f'modify orders {e}')


async def do_orders(quotes):
    """
    processed by websocket
    """
    global buy_pipe, sell_pipe, BUY_OPEN, SELL_OPEN
    # are broker buy orders open in ?
    if any(BUY_OPEN):
        lst_cp = deepcopy(BUY_OPEN)
        BUY_OPEN = _modify_orders(lst_cp, 1, quotes)
        return 1
    elif any(buy_pipe):
        for o in buy_pipe:
            ltp = get_ltp_fm_chain(o['symbol'], quotes)
            o['price'] = ltp + (1*buff)
            order_id = _order_place(o)
            if order_id:
                BUY_OPEN.append(order_id)
                logging.info(f'buy order {order_id} placed')
            else:
                logging.warning('buy order failed')
        buy_pipe = []
        return 2
    elif SELL_OPEN:
        lst_cp = deepcopy(SELL_OPEN)
        SELL_OPEN = _modify_orders(lst_cp, -1, quotes)
        return -1
    elif sell_pipe:
        for o in sell_pipe:
            ltp = get_ltp_fm_chain(o['symbol'], quotes)
            o['price'] = ltp - (1*buff)
            order_id = _order_place(o)
            if order_id:
                SELL_OPEN.append(order_id)
                logging.info(f'sell order {order_id} placed')
            else:
                logging.warning(f'sell order {o} failed')
        sell_pipe = []
        return -2
    return 0

ws_cm = ConnectionManager()
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
tmp = Jinja2Templates(directory='templates')


async def slp_til_next_sec():
    t = dt.now()
    interval = t.microsecond / 1000000
    await asyncio.sleep(1)
    return interval


@app.post("/orders")
def post_orders(
    oqty: Optional[List[str]] = Form(),
    inp: str = Form(), do: str = Form(),
    tsym: List[str] = Form(),
    odir: Optional[List[str]] = Form(),
    chk: Optional[List[str]] = Form()
):
    def upordn(old_sym: str, mv_by: int):
        if old_sym.endswith('CE'):
            old_strk = re.search(r"(\d{5})+?CE?", old_sym).group(0)[:-2]
        elif old_sym.endswith('PE'):
            old_strk = re.search(r"(\d{5})+?PE?", old_sym).group(0)[:-2]
        new_strk = int(old_strk) + (mv_by * dct_build['addsub'])
        new_sym = old_sym.replace(old_strk, str(new_strk))
        return new_sym

    global buy_pipe, sell_pipe, POSITIONS

    if (do == 'up') or (do == 'dn'):
        if len(chk) > 0 and int(inp) > 0:
            pos = deepcopy(POSITIONS)
            for sym in chk:
                if sym in pos:
                    o = {}
                    o['exchange'] = pos[sym]['exchange']
                    o['order_type'] = 'LIMIT'
                    o['product'] = pos[sym]['product']
                    o['quantity'] = abs(pos[sym]['quantity'])
                    c = deepcopy(o)
                    o['symbol'] = pos[sym]['symbol']
                    mv_by = int(inp) if do == 'up' else int(inp) * -1
                    logging.info(f'mv_by  {mv_by}')
                    new_sym = upordn(pos[sym]['symbol'], mv_by)
                    c['symbol'] = new_sym
                    c['side'] = pos[sym]['side']
                    if pos[sym]['side'] == 'SELL':
                        o['side'] = 'BUY'
                        buy_pipe.append(o)
                        sell_pipe.append(c)
                    else:
                        o['side'] = 'SELL'
                        sell_pipe.append(o)
                        buy_pipe.append(c)

    if do == 'send':
        for k, quantity in enumerate(oqty):
            if quantity != "":
                o = {}
                o['exchange'] = dct_build['opt_exch']
                o['side'] = odir[k]
                o['order_type'] = 'LIMIT'
                o['product'] = 'NRML'
                o['quantity'] = quantity
                o['symbol'] = tsym[k]
                if odir[k] == 'BUY':
                    buy_pipe.append(o)
                elif odir[k] == 'SELL':
                    sell_pipe.append(o)

    return {'buy orders': buy_pipe, 'sell orders': sell_pipe}
    # return  { 'oqty': oqty, 'do': do, 'tsym': tsym,
    #         'odir': odir, 'chk': chk }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_cm.connect(websocket)
    global POSITIONS
    data = {}
    data['positions'] = await get_positions()
    while True:
        try:
            data['positions'] = POSITIONS
            data['quotes'] = get_quotes()
            print(data['quotes'])
            interval = 0
            interval = await slp_til_next_sec()
            status = 0
            status = await do_orders(data['quotes'])
            if status > 0 or status < 0:
                data['positions'] = await get_positions()
            atm = oc.get_atm_strike(base_ltp)
            data['time'] = {'slept': interval,
                            'tsym': dct_build['base_script'],
                            'atm': atm,
                            'lot': dct_build['opt_lot'],
                            'ltp': base_ltp}
            is_quotes = data.get('quotes', 0)
            if is_quotes:
                await ws_cm.send_personal_message(json.dumps(data), websocket)
            else:
                interval = sleep(5)
                print("invalid header sent to broker, sleeping")

        except WebSocketDisconnect:
            ws_cm.disconnect(websocket)
            print("websocket disconnected")
            break


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

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
