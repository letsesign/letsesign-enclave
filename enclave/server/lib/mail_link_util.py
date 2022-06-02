import json
import base64
from urllib.parse import urlencode


def gen_confirm_link(signer_app_url, api_version, tid, sid, signer_idx, secret, aux_data, locale, is_phone_verification):
    # compose the confrim data
    confirm_data = {
        "version": api_version,
        "tid": tid,
        "sid": sid,
        "index": signer_idx,
        "secret": secret,
        "aux": aux_data,
        "locale": locale,
        "sms": is_phone_verification
    }

    # combine signer App URL with query string
    url_query_params = {
        "action": "submitIntent",
        "intent": base64.b64encode(json.dumps(confirm_data).encode("utf-8")).decode("utf-8")
    }

    if signer_app_url.find("?") == -1:
        signer_page_url_tail = f"?{urlencode(url_query_params)}"
    else:
        signer_page_url_tail = f"&{urlencode(url_query_params)}"

    return f"{signer_app_url}{signer_page_url_tail}"
