
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def gen_requests_session():
    retry = Retry(total=5, backoff_factor=0.3,
                  status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()

    session.mount("https://", adapter)

    return session
