import re


def get_ltp_fm_chain(tsym: str, quotes):
    if tsym.endswith('CE'):
        strike = re.search(r"(\d{5})+?CE?", tsym).group(1)[:5]
        strike_price = quotes.get(strike, None)
        if strike_price:
            ltp = strike_price.get('call').get(tsym, None)
            return ltp
    elif tsym.endswith('PE'):
        strike = re.search(r"(\d{5})+?PE?", tsym).group(1)[:5]
        strike_price = quotes.get(strike, None)
        if strike_price:
            ltp = strike_price.get('put').get(tsym, None)
            return ltp
    print(f"{tsym} neither call nor put")
    return None
