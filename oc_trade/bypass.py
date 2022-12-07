from omspy.base import Broker, pre, post
from kiteext.kiteext import KiteExt
from typing import List, Dict
import pyotp


class Bypass(Broker):
    """
    Automated Trading class
    """

    def __init__(self, broker):
        try:
            self.kite = KiteExt()
            if broker.get('enctoken'):
                self.kite.login_using_enctoken(**broker)
            else:
                otp = pyotp.TOTP(broker["totp"])
                del broker["totp"]
                pin = otp.now()
                broker['pin'] = f"{int(pin):06d}"
                self.kite.login_with_credentials(**broker)
            super(Bypass, self).__init__()
        except Exception as err:
            print(f'{err} while init')

    def authenticate(self) -> bool:
        """
        Authenticate the user
        """
        return True

    # @pre

    def order_place(self, **kwargs: List[Dict]):
        """
        Place an order
        """
        order_args = dict(
            variety="regular", validity="DAY"
        )
        order_args.update(kwargs)
        return self.kite.place_order(**order_args)

    def order_modify(self, **kwargs: List[Dict]):
        """
        Modify an existing order
        Note
        ----
        All changes must be passed as keyword arguments
        """
        order_id = kwargs.pop("order_id", None)
        order_args = dict(variety="regular")
        order_args.update(kwargs)
        return self.kite.modify_order(order_id=order_id, **order_args)

    def order_cancel(self, order_id: str, variety):
        """
        Cancel an existing order
        """
        order_id = kwargs.pop("order_id", None)
        order_args = dict(variety="regular")
        order_args.update(kwargs)
        return self.kite.cancel_order(order_id=order_id, **order_args)

    @property
    def profile(self):
        return self.kite.profile()

    @property
    @post
    def orders(self):
        status_map = {
            "OPEN": "PENDING",
            "COMPLETE": "COMPLETE",
            "CANCELLED": "CANCELED",
            "CANCELLED AMO": "CANCELED",
            "REJECTED": "REJECTED",
            "MODIFY_PENDING": "WAITING",
            "OPEN_PENDING": "WAITING",
            "CANCEL_PENDING": "WAITING",
            "AMO_REQ_RECEIVED": "WAITING",
            "TRIGGER_PENDING": "WAITING",
        }
        orderbook = self.kite.orders()
        if orderbook:
            for order in orderbook:
                order["status"] = status_map.get(order["status"])
            return orderbook
        else:
            return [{}]

    @property
    @post
    def trades(self) -> List[Dict]:
        tradebook = self.kite.trades()
        if tradebook:
            return tradebook
        else:
            return [{}]

    @property
    @post
    def positions(self):
        position_book = self.kite.positions().get("day")
        if position_book:
            for position in position_book:
                if position["quantity"] > 0:
                    position["transaction_type"] = "BUY"
                else:
                    position["transaction_type"] = "SELL"
            return position_book
        return [{}]

    @property
    def margins(self):
        return self.kite.margins()

    def ltp(self, exchsym):
        return self.kite.ltp(exchsym)
