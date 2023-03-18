from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger
from toolkit.conman import ConnectionManager
from datetime import datetime as dt
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from oc_builder import Oc_builder
import pandas as pd
import uvicorn
import json
import asyncio
import re
from copy import deepcopy
import inspect
from time import sleep
from quotes import option_chain
from orders import get_ltp_fm_chain, _modify_orders, _order_place
from login_get_kite import get_kite

api = ""  # "" is zerodha, optional bypass
# points to add/sub to ltp for limit orders
buff = 2
sym = 'NIFTY'

sec_dir = "../../confid/"
logging = Logger(20, sec_dir + 'oc-trade.log')
# toolkit modules
u = Utilities()
f = Fileutils()
kite = get_kite(api, sec_dir)

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
ulying = kite.ltp(dct_build['base_script'])
base_ltp = ulying[dct_build['base_script']]["last_price"]

# more settings for builder
atm = oc.get_atm_strike(base_ltp)
exchsym = oc.get_syms_fm_atm(atm)


def get_quotes(brkr=None):
    if brkr:
        global kite
        kite = brkr
    try:
        dctcopy = deepcopy(exchsym)
        dctcopy.append(dct_build['base_script'])
        resp = kite.ltp(dctcopy)
        row = {}
        if any(resp):
            global base_ltp
            base_ltp = resp[dct_build['base_script']]["last_price"]
            del resp[dct_build['base_script']]
            row = option_chain(resp)
    except Exception as e:
        logging.info(f'get quotes {e}')
        sleep(1)
        kite = get_kite(api)
        get_quotes(kite)
    else:
        return row


POSITIONS = {}


async def get_positions():
    global POSITIONS
    pos = kite.positions
    data = {}
    if any(pos):
        for d in range(len(pos)):
            data[pos[d]['symbol']] = pos[d]
    POSITIONS = data
    return data

buy_pipe, sell_pipe, BUY_OPEN, SELL_OPEN = [], [], [], []


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


async def slp_til_next_sec():
    t = dt.now()
    interval = t.microsecond / 1000000
    await asyncio.sleep(1)
    return interval

ws_cm = ConnectionManager()
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
tmp = Jinja2Templates(directory='templates')


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
    bk = kite.orders
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
    bk = kite.positions
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
    bk = kite.trades
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
