from toolkit.logger import Logger
import requests
import pyotp
from kiteconnect import KiteConnect
import sys

logging = Logger(10)
LOGINURL = "https://kite.zerodha.com/api/login"
TWOFAURL = "https://kite.zerodha.com/api/twofa"


def Zerodha(user_id, password, totp, api_key, secret, tokpath):
    try:
        session = requests.Session()
        session_post = session.post(LOGINURL, data={
            "user_id": user_id, "password": password}).json()
        logging.debug(f"{session_post=}")
        if (
            session_post and
            isinstance(session_post, dict) and
            session_post['data'].get('request_id', False)
        ):
            request_id = session_post["data"]["request_id"]
            logging.debug(f"{request_id=}")
        else:
            raise ValueError("Request id is not found")
    except ValueError as ve:
        logging.error(f"ValueError: {ve}")
        sys.exit(1)  # Exit with a non-zero status code to indicate an error
    except requests.RequestException as re:
        logging.error(f"RequestException: {re}")
        sys.exit(1)
    except Exception as e:
        # Handle other unexpected exceptions
        logging.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

    try:
        # Generate a TOTP token
        totp = pyotp.TOTP(totp)
        twofa = totp.now()

        # Prepare the data for the 2FA request
        data = {
            "user_id": user_id,
            "request_id": request_id,
            "twofa_value": twofa
        }

        # Perform the 2FA request
        response = session.post(TWOFAURL, data=data)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Get the request token from the redirect URL
        session_get = session.get(
            f"https://kite.trade/connect/login?api_key={api_key}")
        session_get.raise_for_status()  # Raise an exception for HTTP errors

        split_url = session_get.url.split("request_token=")
        if len(split_url) >= 2:
            request_token = split_url[1].split("&")[0]
            logging.debug(f"{request_token=}")
        else:
            raise ValueError("Request token not found in the URL")

    except requests.RequestException as re:
        # Handle network-related errors, including HTTP errors
        logging.error(f"RequestException: {re}")
        sys.exit(1)
    except pyotp.utils.OtpError as otp_error:
        # Handle TOTP generation errors
        logging.error(f"TOTP Generation Error: {otp_error}")
        sys.exit(1)
    except ValueError as value_error:
        # Handle the case where the request token is not found
        logging.error(f"ValueError: {value_error}")
        sys.exit(1)
    except Exception as e:
        # Handle other unexpected exceptions
        logging.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

    try:
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=secret)
        logging.debug(f"{data=}")
        if (
            data and
            isinstance(data, dict) and
            data.get('access_token', False)
        ):
            logging.debug(f"{data['access_token']}")
            with open(tokpath, 'w') as tok:
                tok.write(data['access_token'])
            return kite
        else:
            raise ValueError(f"Unable to generate session: {str(data)}")
    except Exception as e:
        # Handle any unexpected exceptions
        logging.exception(f"when generating session: {e}")
        sys.exit(1)
