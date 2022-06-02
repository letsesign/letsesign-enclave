import json
import logging
import traceback

import requests

from lib.costant_data import APIPathList

CHUNK_SIZE = 1024 * 1024
API_SERVER_URL = "http://127.0.0.1"
MAX_RESPONSE_SIZE = 1024 * 1024 * 50  # 50MB


def __read_chucks(res):
    data_size = 0
    data_bytes = bytearray()

    # check "Content-Length" header
    if int(res.headers.get("Content-Length")) > MAX_RESPONSE_SIZE:
        raise ValueError("response data exceeds size limit")

    # check the sum of check size
    for chunk in res.iter_content(CHUNK_SIZE):
        data_size += len(chunk)

        if data_size > MAX_RESPONSE_SIZE:
            raise ValueError(f"response data exceeds size limit: {data_size}")
        else:
            data_bytes.extend(chunk)

    return json.loads(data_bytes.decode("utf-8"))


def get_job_api():
    try:
        # get job data from host instance
        with requests.get(f"{API_SERVER_URL}/api/{APIPathList.GET_JOB}", stream=True, timeout=10) as res:
            res.raise_for_status()

            return __read_chucks(res)
    except requests.Timeout as e:
        logging.error(e)
    except requests.ConnectionError as e:
        pass
    except BaseException as e:
        logging.error(traceback.format_exc())

    return None


def put_job_result_api(session, result):
    try:
        # put job result to host instance
        with requests.post(f"{API_SERVER_URL}/api/{APIPathList.PUT_JOB_RESULT}", json={"session": session, "jobResult": result}, stream=True, timeout=10) as res:
            res.raise_for_status()

            return __read_chucks(res)
    except requests.Timeout as e:
        logging.error(e)
    except requests.ConnectionError as e:
        pass
    except BaseException as e:
        logging.error(traceback.format_exc())

    return None
