import json
import logging
import traceback

import cbor2

from lib import libnsm_util
from lib import attest_doc_verifier

DOWNWARD_COMP_VERSION = []


def __check_version_with_current_enclave(pcrs):
    enclave_attest_doc = libnsm_util.nsm_lib_get_attestation_doc(None, None)
    enclave_attest_doc_cose = cbor2.loads(enclave_attest_doc)
    enclave_attest_doc_data = cbor2.loads(enclave_attest_doc_cose[2])

    # check PCR0 ~ PCR2
    for pcr_idx in range(3):
        if pcrs[pcr_idx].hex() != enclave_attest_doc_data["pcrs"][pcr_idx].hex():
            logging.debug(f"mismatch PCR {pcr_idx}")
            return False

    return True


def __check_version_with_downward_enclave(pcrs):
    for doward_version in DOWNWARD_COMP_VERSION:
        for pcr_idx in range(3):
            if pcrs[pcr_idx].hex() != doward_version["pcrs"][str(pcr_idx)]:
                logging.debug(f"mismatch PCR {pcr_idx}")
                break
        else:
            return True

    return False


def gen_attest_document(fn_name, hash_list):
    return libnsm_util.nsm_lib_get_attestation_doc(json.dumps({
        "fnName": fn_name,
        "hashList": hash_list
    }, ensure_ascii=False, separators=(',', ':')).encode("utf-8"), None)


def check_attest_document(attest_document_bytes):
    try:
        # check attest document
        attest_doc_data = attest_doc_verifier.verify_attestation_doc(
            attest_document_bytes, True)

        # check enclave version
        if not __check_version_with_current_enclave(attest_doc_data["pcrs"]):
            if not __check_version_with_downward_enclave(attest_doc_data["pcrs"]):
                return False, None, None, None

        user_data = json.loads(attest_doc_data["user_data"].decode("utf-8"))

        return True, user_data["fnName"], user_data["hashList"], attest_doc_data["timestamp"]
    except BaseException as e:
        logging.error(traceback.format_exc())

    return False, None, None, None
