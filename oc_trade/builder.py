from typing import Dict


class Builder:

    def __init__(self, dct_build):
        self.dct_build = dct_build

    def get_atm_strike(self, base_ltp_on_start: float):
        if base_ltp_on_start == self.dct_build['sample']:
            return self.dct_build['sample']
        elif base_ltp_on_start > self.dct_build['sample']:
            diff = base_ltp_on_start-self.dct_build['sample']
            nof_step = diff/self.dct_build['addsub']
            if nof_step >= 1:
                ret = int(nof_step)*self.dct_build['addsub']
                ret = self.dct_build['sample'] + ret
                return ret
            else:
                return self.dct_build['sample']
        elif base_ltp_on_start < self.dct_build['sample']:
            diff = self.dct_build['sample']-base_ltp_on_start
            nof_step = diff/self.dct_build['addsub']
            if nof_step >= 1:
                ret = int(nof_step)*self.dct_build['addsub']
                ret = self.dct_build['sample'] - ret
                return ret
            else:
                return self.dct_build['sample']

    def get_syms_fm_atm(self, atm: int) -> Dict:
        lst_strikes = []
        lst_strikes.append(atm)
        for r in range(self.dct_build['abv_atm']):
            lst_strikes.append(atm + ((r+1)*self.dct_build['addsub']))
        for r in range(self.dct_build['abv_atm']):
            lst_strikes.append(atm - ((r+1)*self.dct_build['addsub']))
        # lst_strikes = sorted(lst_strikes, reverse=True)
        exchsym = []
        for strike in lst_strikes:
            call = self.dct_build['opt_exch'] + ':' + self.dct_build['base_name'] + \
                self.dct_build['expiry'] + str(strike) + 'CE'
            put = self.dct_build['opt_exch'] + ':' + self.dct_build['base_name'] + \
                self.dct_build['expiry'] + str(strike) + 'PE'
            exchsym.append(call)
            exchsym.append(put)
        return exchsym
