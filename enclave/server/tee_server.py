import time
import base64
import hashlib
import logging
import traceback

from lib import pdf_tool_util
from lib import rest_api_util
from lib import params_checker
from lib import attest_doc_util
from lib.costant_data import JobNameList
from lib.err_code_util import ErrCodeList
from functions.fn_send_req_handler import SendReqHandler
from functions.fn_attach_esig_handler import AttachESigHandler
from functions.fn_confirm_intent_handler import ConfirmIntentHandler

logging.basicConfig(
    format='[%(asctime)s][%(levelname)s][%(process)d][%(filename)s][%(lineno)d]: %(message)s', level=logging.INFO)


def __process_job_data(job_data):
    response = {}

    try:
        logging.debug("Execute job handler")

        # execute job handler by job name
        if job_data["jobName"] == JobNameList.SEND_REQ:
            job_handler = SendReqHandler(job_data["jobData"])
            code, fn_res_list, _ = job_handler.do_job()
        elif job_data["jobName"] == JobNameList.CONFIRM_INTENT:
            job_handler = ConfirmIntentHandler(job_data["jobData"])
            code, fn_res_list, twilio_verification_sid = job_handler.do_job()
        elif job_data["jobName"] == JobNameList.ATTACH_ESIG:
            job_handler = AttachESigHandler(job_data["jobData"])
            code, fn_res_list, _ = job_handler.do_job()
        else:
            code = ErrCodeList.INVALID_PARAM.value

        response["code"] = code

        logging.debug(f"Job handler return code: {code}")

        # generate proof of job result
        if code == ErrCodeList.SUCCES.value:
            logging.debug("generate proof of job result")

            results = []
            hash_list = []

            for fn_res in fn_res_list:
                results.append({"name": fn_res["name"], "data": base64.b64encode(
                    fn_res["bytes"]).decode("utf-8")})

                hash_list.append(
                    {"name": fn_res["name"], "hash": hashlib.sha256(fn_res["bytes"]).hexdigest()})

            attest_document_bytes = attest_doc_util.gen_attest_document(
                job_data["jobName"], hash_list)
            attest_document_b64 = base64.b64encode(
                attest_document_bytes).decode("utf-8")

        # export the response
        if code == ErrCodeList.SUCCES.value:
            if job_data["jobName"] == JobNameList.SEND_REQ:
                response["results"] = results
                response["attestDocument"] = attest_document_b64
            elif job_data["jobName"] == JobNameList.CONFIRM_INTENT:
                response["results"] = results
                response["attestDocument"] = attest_document_b64
            elif job_data["jobName"] == JobNameList.ATTACH_ESIG:
                job_handler.notify_result(results, attest_document_b64)

                tmp_encrypted_result = job_handler.encrypt_result(
                    results, attest_document_b64)

                if tmp_encrypted_result:
                    response["encryptedResult"] = tmp_encrypted_result
                else:
                    response["code"] = ErrCodeList.ENCRYPT_RESULT_FAIL.value
        else:
            if job_data["jobName"] == JobNameList.CONFIRM_INTENT:
                if code == ErrCodeList.WAITING_VERIFICATION_PIN_CODE.value:
                    response["twilioVerificationSID"] = twilio_verification_sid
    except BaseException as e:
        logging.error(traceback.format_exc())
        response["code"] = ErrCodeList.UNDEFINED_ERROR.value

    # put job result
    try:
        logging.debug("put job result to host instance")
        rest_api_util.put_job_result_api(job_data["session"], response)
    except BaseException as e:
        logging.error(traceback.format_exc())


def main():
    logging.info("Let's eSign TEE server start...")

    logging.getLogger("twilio").setLevel(logging.ERROR)

    pdf_tool_util.init()

    while True:
        try:
            # get job
            get_job_res = rest_api_util.get_job_api()

            if get_job_res is not None and len(get_job_res.keys()) > 0:
                if params_checker.verify_param_with_schema(get_job_res, params_checker.get_job_params_schema):
                    logging.debug(
                        f"Job received: session - {get_job_res['session']}, job name - {get_job_res['jobName']}")

                    __process_job_data(get_job_res)
        except BaseException as e:
            logging.error(traceback.format_exc())

        time.sleep(0.1)


if __name__ == "__main__":
    main()
