from typing import List, Dict
import re
from toolkit.logger import Logger
from login_get_kite import get_kite

buff = 2

logging = Logger()
bypass = get_kite()


# more settings for builder
buy_pipe, sell_pipe, BUY_OPEN, SELL_OPEN = [], [], [], []


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


def get_orders():
    order_book = bypass.orders
    data = {}
    if any(order_book):
        for page in order_book:
            order_id = page['order_id']
            data[order_id] = page
    return data


def _modify_orders(lst: List, dirtn: int, quotes: Dict):
    try:
        book = get_orders()
        if any(book):
            for o in lst:
                status = book[o]['status']
                logging.info(f'{book[o]["order_id"]} is {status}')
                if status == 'REJECTED' or status == 'CANCELLED' or status == 'COMPLETE':
                    lst.pop()
                    logging.info('removing')
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
