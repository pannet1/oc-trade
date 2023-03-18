import re
from time import sleep
from datetime import datetime as dt
from toolkit.logger import Logger

logging = Logger()


def option_chain(resp):
    """
    consumed by websocket for display
    """
    try:
        row = {}
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


def slp_til_next_sec():
    t = dt.now()
    interval = t.microsecond / 1000000
    sleep(interval)
    return interval


