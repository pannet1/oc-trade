from toolkit.fileutils import Fileutils
from toolkit.logger import Logger
from omspy_brokers.bypass import Bypass
from omspy.brokers.zerodha import Zerodha
logging = Logger(20, 'app.log')


f = Fileutils()
sec_dir = '../../../confid/'


def get_kite(api=""):
    kite = False
    if api == "bypass":
        kite = _get_bypass()
    else:
        kite = _get_bypass()
        kite.authenticate()
    return kite


def _get_bypass():
    try:
        lst_c = f.get_lst_fm_yml(sec_dir + 'bypass.yaml')
        tokpath = sec_dir + lst_c['userid'] + '.txt'
        enctoken = None
        if f.is_file_not_2day(tokpath) is False:
            logging.info(
                f'token file modified today ... reading enctoken {enctoken}')
            """
            with open(tokpath, 'r') as tf:
                enctoken = (
                    tf.read().decode('utf-8').strip()
                    if isinstance(tf.read(), bytes)
                    else tf.read().strip()
                )

            """
            with open(tokpath, 'r') as tf:
                enctoken = tf.read()
                if len(enctoken) < 5:
                    enctoken = None
        logging.info(f'enctoken to broker {enctoken}')
        bypass = Bypass(lst_c['userid'],
                        lst_c['password'],
                        lst_c['totp'],
                        tokpath,
                        enctoken)
        if bypass.authenticate():
            if not enctoken:
                enctoken = bypass.kite.enctoken
                with open(tokpath, 'w') as tw:
                    tw.write(enctoken)
    except Exception as e:
        logging.error(f"unable to create broker object {e}")
    else:
        return bypass

    def _get_zerodha():
        try:
            fdct = f.get_lst_fm_yml(sec_dir + 'zerodha.yaml')
            zera = Zerodha(user_id=fdct['userid'],
                           password=fdct['password'],
                           totp=fdct['totp'],
                           api_key=fdct['api_key'],
                           secret=fdct['secret'],
                           tokpath=sec_dir + fdct['userid'] + '.txt'
                           )
        except Exception as e:
            logging.error(f"unable to create broker object {e}")
            # raise SystemExit(0)
        else:
            return zera
