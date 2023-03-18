from typing import List
import yaml
from toolkit.scripts import Strikes
from pydantic import ValidationError


class Oc_builder:

    def __init__(self, lst_build_files: List, build_path: str):
        lst_valid_builds = []
        for build_file in lst_build_files:
            with open(build_path + build_file, "r") as f:
                lst_not_validated = yaml.safe_load(f)
            try:
                Strikes(**lst_not_validated)
                lst_valid_builds.append(lst_not_validated)
            except ValidationError as v:
                print(f'validation error {v}')
        self.lst_valid_builds = lst_valid_builds

    def set_symbol_dict(self, sym: str):
        # verify if our target option base symbol is
        # in the validated build file
        for build_dict in self.lst_valid_builds:
            dct_build = []
            if sym == build_dict['base_name']:
                print(f'{sym} found')
                dct_build = build_dict
                break
        # if not found exit
        if not any(dct_build):
            print(f' {sym} not found in {dct_build} ')
            self.dct_build = {}
        else:
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

    def get_syms_fm_atm(self, atm) -> List:
        dct_build = self.dct_build
        lst_strikes = []
        lst_strikes.append(atm)
        for r in range(dct_build['abv_atm']):
            lst_strikes.append(atm + ((r+1)*dct_build['addsub']))
        for r in range(dct_build['abv_atm']):
            lst_strikes.append(atm - ((r+1)*dct_build['addsub']))
        # lst_strikes = sorted(lst_strikes, reverse=True)
        exchsym = []
        for strike in lst_strikes:
            call = dct_build['opt_exch'] + ':' + dct_build['base_name'] + \
                dct_build['expiry'] + str(strike) + 'CE'
            put = dct_build['opt_exch'] + ':' + dct_build['base_name'] + \
                dct_build['expiry'] + str(strike) + 'PE'
            exchsym.append(call)
            exchsym.append(put)
        return exchsym
