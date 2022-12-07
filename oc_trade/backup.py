from toolkit.bypass import Bypass
from toolkit.fileutils import Fileutils
from toolkit.scripts import Strikes
from toolkit.utilities import Utilities
from toolkit.logger import Logger
from pydantic import ValidationError
from datetime import datetime as dt
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from connection_manager import ConnectionManager
import sys
import json
import asyncio
import re
import copy as cp


class Oc_trade:

    #TODO
    sym = 'NIFTY'
    buy_pipe, sell_pipe, BUY_OPEN, SELL_OPEN  = [], [], [], []

    # toolkit modules
    u = Utilities()
    f = Fileutils()
    logging = Logger(20)

    def get_atm_strike(self):
        if self.base_ltp==self.dct_build['sample']:
            self.atm = self.dct_build['sample']
        elif self.base_ltp>self.dct_build['sample']:
            diff = self.base_ltp-self.dct_build['sample']
            nof_step = diff/self.dct_build['addsub']
            if nof_step>=1:
                ret = int(nof_step)*self.dct_build['addsub'] 
                ret = self.dct_build['sample'] + ret
                self.atm = ret
            else:
                self.atm = self.dct_build['sample']
        elif self.base_ltp<self.dct_build['sample']:
            diff = self.dct_build['sample']-o
            nof_step = diff/self.dct_build['addsub']
            if nof_step >=1:
                ret = int(nof_step)*self.dct_build['addsub'] 
                ret = self.dct_build['sample'] - ret
                self.atm = ret
            else:
                self.atm = self.dct_build['sample']


    def get_strikes(self)->List:
        lst_strikes = []
        lst_strikes.append(self.atm)
        for r in range(self.dct_build['abv_atm']):
            lst_strikes.append(self.atm + ((r+1)*self.dct_build['addsub']) )
        for r in range(self.dct_build['abv_atm']):
            lst_strikes.append(self.atm - ((r+1)*self.dct_build['addsub']) )
        #lst_strikes = sorted(lst_strikes, reverse=True)
        self.lst_strikes = lst_strikes

    def set_sym_fm_strk(self)->List:
        self.exchsym = []
        for strike in self.lst_strikes:
            call = self.dct_build['opt_exch'] + ':' + self.dct_build['base_name'] + self.dct_build['expiry'] + str(strike) + 'CE'
            put = self.dct_build['opt_exch'] + ':' + self.dct_build['base_name'] + self.dct_build['expiry'] + str(strike) + 'PE'
            self.exchsym.append(call)
            self.exchsym.append(put)

    def __init__(self):
        BUILD_PATH = "strikes/"
        # validate option build dict files
        lst_build_files = self.f.get_files_with_extn('yaml', BUILD_PATH)
        lst_valid_builds = []
        for build_file in lst_build_files:
            lst_not_validated = self.f.get_lst_fm_yml(BUILD_PATH + build_file)
            try:
                Strikes(**lst_not_validated)
                lst_valid_builds.append(lst_not_validated)
            except ValidationError as v:
                logging.warn(f'validation error {v}')
                sys.exit()

        # verify if our target option base symbol is 
        # in the validated build file 
        for build_dict in lst_valid_builds:
            dct_build = []
            if sym == build_dict['base_name']:
                logging.info(f'{sym} found')
                self.dct_build = build_dict
                break

        # if not found exit
        if not any(build_dict): 
            logging.error(f' {sym} not found in {build_dict} ')
            sys.exit()

        # init broker object 
        lst_credential = self.f.get_lst_fm_yml('../../../confid/bypass.yaml')
        self.kite = Bypass(lst_credential)

        base_script = self.dct_build['base_script']
        ulying = kite.ltp(base_script)
        self.base_ltp = ulying[base_script]["last_price"]

    def get_quotes(self):
        resp = {}
        resp = self.kite.ltp(self.exchsym)
        self.base_ltp = resp[self.dct_build['base_script']]["last_price"]
        del resp[self.dct_build['base_script']]
        row = {}
        option_types_n_strikes = [
            (tradingsymbol, "CALL", re.search(r"\d+?CE?", tradingsymbol).group(0)[:-2])
            if tradingsymbol.endswith("CE")
            else (tradingsymbol, "PUT", re.search(r"\d+?PE?", tradingsymbol).group(0)[:-2])
            for tradingsymbol in [key.split(":")[-1] for key in resp.keys()]
        ]
        try:
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
                    {"put": {tradingsymbol: resp[f"NFO:{tradingsymbol}"]["last_price"]}}
                )
                for tradingsymbol, option_type, strike_price in option_types_n_strikes
                if option_type == "PUT"
            ]
        except Exception as b:
            logging.warn(f"exception {b}")
        else:
            return row

    def order_place(self, order: List):
        resp_order = self.kite.place_order(**order)
        if not isinstance(resp_order, list):
            return None
        elif resp_order.get('status') == 'success' and resp_order.get('data'):   
            order_id = resp_order['data']['order_id']
            return order_id

    def get_order_book(self):
        order_book = self.kite.orders()
        #with open('tests/success_orders.json', 'r') as json_f:
            #order_book = json.load(json_f)
        data = {}
        if isinstance(order_book, list):
            order_book = order_book[0]
        else:
            print(order_book)
            type(order_book)
            return data

        if order_book.get('status') == 'success' and order_book.get('data') is not None:
            for page in order_book.get('data'):
                order_id = page['order_id']
                data[order_id] = page
        return data

    def test_get_positions(self):
        with open("./tests/positions.json") as json_f:
            pos = json.load(json_f)
        return pos

    def get_positions(self):
        #pos = kite.positions()
        pos = test_get_positions()
        if pos.get('status') == 'success' and pos.get('data') is not None:
            day = pos.get('data').get('day')
            if day is not None:            
                intraday =  {}
                for d in day:
                    intraday[d['tradingsymbol']] = d
                return intraday
            else:
                return day

    def get_ltp_fm_chain(self,tsym:str, option_chain: List):
        if tsym.endswith('CE'):
            strike = re.search(r"\d+?CE?", tsym).group(0)[:-2]
            ltp = option_chain.get(strike).get('call').get(tsym)
            return ltp
        elif tsym.endswith('PE'):
            strike = re.search(r"\d+?PE?", tsym).group(0)[:-2]
            ltp = option_chain.get(strike).get('put').get(tsym)
            return ltp
        else:
            raise Exception("tsym neither call nor put")
    
failed_orders = {[]}
no_data = { 'status': 'success', 'data':[]}

def do_orders(option_chain):
    #global buy_pipe, sell_pipe, BUY_OPEN, SELL_OPEN
    #BUY_OPEN = ['1','2','3','4']
    # are broker buy orders open in ?
    is_loop = len(self.BUY_OPEN)
    if is_loop>0:
        book = get_order_book()
        if len(book)>0:            
            lst_cp = cp.copy(self.BUY_OPEN)
            for o in lst_cp:
                status = book[o]['status']
                if status == 'COMPLETE' or status=='CANCELLED':
                    self.BUY_OPEN.remove(o)
                elif status == 'OPEN':
                    logging.info(f'modifying order: {o}')
                else:
                    logging.debug(f'unknown status {status}')
            logging.debug(f'self.BUY_OPEN {self.BUY_OPEN}')
        else:
            is_loop = 0
            logging.warning("orderbook is empty")

    # yes, broker buy orders processed
    if is_loop>0:
        return False
    else:
        is_loop = len(self.buy_pipe)
   
    # posted buy orders in pipline ?
    if is_loop>0:
        lst_cp = cp.copy(self.buy_pipe)
        for o in lst_cp:
            try:
                ltp = get_ltp_fm_chain(o['tradingsymbol'],option_chain)        
                o['price'] = ltp
                order_id = order_place(o)
                self.BUY_OPEN.append(order_id)
                self.buy_pipe.remove(o)
                logging.debug('buy order place')
            except Exception as e:
                logging.warning(e)

    # posted buy orders processed ?
    if is_loop>0:
        return
    else:
        is_loop = len(self.SELL_OPEN)

    # open sell orders
    if is_loop>0:
        book = get_order_book()
        if len(book)>0:            
            lst_cp = cp.copy(self.SELL_OPEN)
            for o in lst_cp:
                status = book[o]['status']
                if status == 'COMPLETE' or status=='CANCELLED':
                    self.SELL_OPEN.remove(o)
                elif status == 'OPEN':
                    logging.info(f'modifying order: {o}')
                else:
                    logging.debug(f'unknown status {status}')
            logging.debug(f'self.SELL_OPEN {self.SELL_OPEN}')
        else:
            is_loop = 0
            logging.warning("orderbook is empty")

    # open sell orders processed ?
    if is_loop>0:
        return False
    else:
        is_loop = len(self.sell_pipe)
   
    # new sell orders
    if is_loop>0:
        lst_cp = cp.copy(self.sell_pipe)
        for o in lst_cp:
            try:
                order_id = order_place(o)
                self.SELL_OPEN.append(order_id)
                self.sell_pipe.remove(o)
                logging.debug('sell order place')
            except Exception as e:
                logging.warning(e)


oc = Oc_trade()
oc.set_atm_strike()
oc.set_strikes()        
oc.set_sym_fm_strk()

ws_cm = ConnectionManager()
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Option Chain Trader</title>
        <link
        href="https://fonts.googleapis.com/css?family=Rock+Salt"
        rel="stylesheet"
        type="text/css" />
        <link href="./static/pico.slim.css" rel="stylesheet" type="text/css">
    <script src="./static/index.js"></script>
    </head>
    <body>
        <form method='post' target="_blank" action='/orders/' id="frm" autocomplete="off">
        <table role='grid' border='1px solid black'> 
            <caption>option chain</caption>
            <thead>
                <tr>
                   <th colspan='2' scope="column">
                    <button class="pushable" type="button" onclick='batch_orders(this.innerText)'>
                      <span class="shadow"></span>
                      <span class="edge edge-green"></span>
                      <span class="front front-green">
                        BUY
                      </span>
                    </button>
                    </th>
                    <th colspan='2' style='text-align:center' scope="column">
                        Calls
                    </th>
                    <th colspan='2' scope="column">
                        <button name='do' value='up'>UP</button>
                    </th>
                    <th scope="column">
                        <input class='center' id="inp" name="inp" type="number" value=1 min=1>
                    </th>
                    <th colspan='2' scope="column">
                        <button value='dn' name='do'>Dn</button>
                    </th>
                    <th colspan='2' style='text-align:center' scope="column">
                        Puts
                    </th>
                    <th colspan='2' scope="column">
                      <button class="pushable" type="button" onclick='batch_orders(this.innerText)'> 
                      <span class="shadow"></span>
                        <span class="edge edge-red"></span>
                        <span class="front front-red">
                          SELL
                        </span>
                    </button>
                    </th>
                </tr>
            </thead>
            <tbody id="messages">                            
            </tbody>
            <tfoot>
                <tr>
                  <td>&nbsp;</td>
                  <td>&nbsp;</td>
                  <td id="slept" colspan='2' class='center'>time</td>
                  <td>&nbsp;</td>
                  <td>&nbsp;</td>
                  <td id="tsym" class='center'>time</td>
                  <td>&nbsp;</td>
                  <td>&nbsp;</td>
                  <td id="ltp" colspan='2' class='center'>time</td>
                  <td>&nbsp;</td>
                  <td>&nbsp;</td>
                </tr>
            </tfoot>
        </table>
        </form>
    </body>
</html>
"""

async def slp_til_next_sec():
    t = dt.now()
    interval = t.microsecond / 1000000
    await asyncio.sleep(interval)
    return interval

@app.post("/orders")
async def post_orders(
    oqty: Optional[List[str]] = Form(),  
    inp: str = Form(),
    tsym: List[str] = Form(), 
    odir: Optional[List[str]] = Form()):
    self.buy_pipe, self.sell_pipe
    
    for k, quantity in enumerate(oqty):
        if quantity != "":
            o = {}
            o['variety'] = 'regular'
            o['exchange'] = self.dct_build['opt_exch']
            o['transaction_type'] = odir[k]
            o['order_type'] = 'LIMIT'
            o['product'] = 'NRML'            
            o['quantity'] = quantity
            o['validity'] = 'DAY'
            if odir[k] == 'BUY':
                o['tradingsymbol'] = tsym[k]
                self.buy_pipe.append(o)
            else:
                o['tradingsymbol'] = tsym[k]
                self.sell_pipe.append(o)
    
    return  {'buy orders': self.buy_pipe , 'sell orders': sell_pipe}

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
            atm = get_atm_strike(self.dct_build, self.base_ltp)
            data['time'] = { 'slept': interval,
                'tsym': self.dct_build['base_script'], 
                'atm': atm,
                'ltp': self.base_ltp }
            await ws_cm.send_personal_message(json.dumps(data), websocket)
    except WebSocketDisconnect:
        ws_cm.disconnect(websocket)

@app.get("/")
async def get():
    return HTMLResponse(html)

