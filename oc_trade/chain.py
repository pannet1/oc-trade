import re


def get_ltp_fm_chain(tsym: str, quotes):
    if tsym.endswith('CE'):
        strike = re.search(r"(\d{5})+?CE?", tsym).group(1)[:5]
        ltp = quotes.get(strike).get('call').get(tsym)
        return ltp
    elif tsym.endswith('PE'):
        strike = re.search(r"(\d{5})+?PE?", tsym).group(1)[:5]
        ltp = quotes.get(strike).get('put').get(tsym)
        return ltp
    else:
        print(f"{tsym} neither call nor put")
