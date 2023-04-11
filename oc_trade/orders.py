from typing import List, Dict
from chain import get_ltp_fm_chain
from enum import Enum


class Orders:
    def __init__(self, kite, logging, buff):
        self.kite = kite
        self.logging = logging
        self.buff = buff
        self.status = Status.EMPTY

    def _order_place(self, order: List):
        """
        orders helper
        """
        try:
            order_id = self.kite.order_place(**order)
            if isinstance(order_id, str):
                return order_id
            else:
                self.logging.warning(f'no order id {order_id}')
        except Exception as e:
            self.logging.warning(f'order place {e}')

    def get_orders(self):
        order_book = self.kite.orders
        data = {}
        if any(order_book):
            for page in order_book:
                order_id = page['order_id']
                data[order_id] = page
        return data

    def _modify_orders(self, lst: List, dirtn: int, quotes: Dict):
        try:
            book = self.get_orders()
            if any(book):
                for o in lst:
                    status = book[o]['status']
                    self.logging.info(f'{book[o]["order_id"]} is {status}')
                    if status == 'REJECTED' or status == 'CANCELLED' or status == 'COMPLETE':
                        lst.pop()
                        self.logging.info('removing')
                    elif status == 'OPEN' or status == 'PENDING':
                        ltp = get_ltp_fm_chain(book[o]['symbol'], quotes)
                        ltp += (self.buff * dirtn)
                        self.logging.info(f'modifying price to {ltp}')
                        try:
                            self.kite.order_modify(
                                price=ltp, order_id=book[o]['order_id'])
                        except Exception as e:
                            lst.pop()
                            self.logging.warning(f'modify orders {e}')
                return lst
            return []
        except Exception as e:
            self.logging.warning(f'modify orders {e}')


class Status(Enum):
    SELL_PIPE = -2
    SELL_OPEN = -1
    EMPTY = 0
    BUY_OPEN = 1
    BUY_PIPE = 2
