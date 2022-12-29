import re

tradingsymbol = 'NIFTY23D0518000CE'
result = re.search(r"(\d{5})+?CE?",tradingsymbol).group(1)[:5]
print(result)
