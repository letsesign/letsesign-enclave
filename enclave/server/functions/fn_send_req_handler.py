import base64
import hashlib
import logging
import traceback

import cbor2
import phonenumbers

from lib import crypto_util
from lib import mail_sender
from lib import pdf_tool_util
from lib import mail_link_util
from lib import params_checker
from lib.err_code_util import ErrCodeList
from functions.fn_base_handler import BaseFunctionHandler

EOF_MARKER = "%%EOF"


class SendReqHandler(BaseFunctionHandler):
    def __init__(self, job_data):
        BaseFunctionHandler.__init__(
            self, job_data, params_checker.send_req_job_schema)

    def do_job_internal(self):
        ret_code = ErrCodeList.UNDEFINED_ERROR.value
        results = []

        try:
            logging.debug(f"signer index: {self.job_data['signerIdx']}")

            # check signerList and signerInfoList
            if len(self.job_data["taskPayload"]["publicTaskInfo"]["templateInfo"]["signerList"]) == len(self.task_config["signerInfoList"]):
                ret_code = ErrCodeList.SUCCES.value
            else:
                ret_code = ErrCodeList.MISMATCH_SIGNER_LIST_LENGTH.value

            # check signer index
            if ret_code == ErrCodeList.SUCCES.value:
                if self.job_data["signerIdx"] >= len(self.task_config["signerInfoList"]):
                    logging.error("invalid signer index")
                    ret_code = ErrCodeList.INVALID_SIGNER_INDEX.value

            # check signer phone number
            if ret_code == ErrCodeList.SUCCES.value:
                for signer_info in self.task_config["signerInfoList"]:
                    if signer_info.get("phoneNumber"):
                        if self.twilio_config is None:
                            logging.error("missing twilio config")
                            ret_code = ErrCodeList.MISSING_TWILIO_CONFIG.value
                            break

                        if not phonenumbers.is_valid_number(phonenumbers.parse(signer_info["phoneNumber"])):
                            logging.error("format of phone number is invalid")
                            ret_code = ErrCodeList.INVALID_PHONE_NUMBER_FORMAT.value
                            break

            # test signed PDF
            if ret_code == ErrCodeList.SUCCES.value:
                if self.__test_signed_pdf(self.template_data):
                    ret_code = ErrCodeList.SIGNED_PDF_DETECTED.value

            # test protected PDF
            if ret_code == ErrCodeList.SUCCES.value:
                if not self.__test_pdf_modifiable(self.job_data["taskPayload"]["publicTaskInfo"]["templateInfo"]["signerList"], self.template_data):
                    ret_code = ErrCodeList.PDF_NOT_MODIFIABLE_DETECTED.value

            # generate preview PDF
            if ret_code == ErrCodeList.SUCCES.value:
                pdf_tool_fields = []

                if self.job_data["taskPayload"]["publicTaskInfo"]["inOrder"]:
                    # preview other signatures and signing hint
                    for signer_idx in range(self.job_data["signerIdx"] + 1):
                        current_signer_info = self.task_config["signerInfoList"][signer_idx]

                        signer_field = {
                            "emailAddr": current_signer_info["emailAddr"],
                            "name": current_signer_info["name"],
                            "locale": current_signer_info["locale"],
                            "fieldList": self.job_data["taskPayload"]["publicTaskInfo"]["templateInfo"]["signerList"][signer_idx]["fieldList"],
                            "signHint": True if signer_idx == self.job_data["signerIdx"] else False
                        }

                        if current_signer_info.get("phoneNumber"):
                            signer_field["phoneNumber"] = current_signer_info["phoneNumber"]

                        pdf_tool_fields.append(signer_field)
                else:
                    # preview signing hint
                    current_signer_info = self.task_config["signerInfoList"][self.job_data["signerIdx"]]

                    signer_field = {
                        "emailAddr": current_signer_info["emailAddr"],
                        "name": current_signer_info["name"],
                        "locale": current_signer_info["locale"],
                        "fieldList": self.job_data["taskPayload"]["publicTaskInfo"]["templateInfo"]["signerList"][self.job_data["signerIdx"]]["fieldList"],
                        "signHint": True
                    }

                    if current_signer_info.get("phoneNumber"):
                        signer_field["phoneNumber"] = current_signer_info["phoneNumber"]

                    pdf_tool_fields.append(signer_field)

                preview_pdf_b64 = pdf_tool_util.gen_preview_pdf(
                    self.template_data, pdf_tool_fields, self.job_data["taskPassword"] if self.job_data["taskPayload"]["publicTaskInfo"]["domainSetting"]["enhancedPrivacy"] else None)
                if preview_pdf_b64 is None:
                    ret_code = ErrCodeList.GENERATE_PREVIEW_PDF_FAIL.value
                else:
                    logging.debug("preview PDF has been generated")

            # generate POR data
            if ret_code == ErrCodeList.SUCCES.value:
                intent_secret = base64.b64encode(
                    crypto_util.gen_random_bytes(256)).decode("utf-8")

                target_signer_info = self.task_config["signerInfoList"][self.job_data["signerIdx"]]

                por_data = {
                    "payloadHash": self.payload_hash,
                    "signerIdx": self.job_data["signerIdx"],
                    "secretHash": hashlib.sha256(intent_secret.encode("utf-8")).hexdigest(),
                    "phoneRequired": True if target_signer_info.get("phoneNumber") else False
                }

                por_data_bytes = cbor2.dumps(por_data)

                logging.debug("POR data has been generated")

            # send confirm mail
            if ret_code == ErrCodeList.SUCCES.value:
                signer_confirm_link = mail_link_util.gen_confirm_link(self.job_data["taskPayload"]["publicTaskInfo"]["domainSetting"]["signerAppURL"], self.job_data["extraData"]["apiVersion"], self.job_data["taskID"], self.job_data[
                                                                      "subTaskID"], self.job_data["signerIdx"], intent_secret, self.job_data["extraData"]["auxData"], target_signer_info["locale"], True if target_signer_info.get("phoneNumber") else False)

                mail_sender_obj = mail_sender.MailSender(self.email_config)
                ret_code = mail_sender_obj.send_signer_confirmation_mail(target_signer_info["locale"], self.job_data["taskPayload"]["publicTaskInfo"]["domainSetting"]["rootDomain"], target_signer_info["emailAddr"], self.job_data[
                                                                         "taskID"], target_signer_info["name"], self.task_config["senderMsg"], self.task_config["fileName"], preview_pdf_b64, signer_confirm_link, target_signer_info.get("phoneNumber"))

                if ret_code == ErrCodeList.SEND_EMAIL_FAIL.value:
                    ret_code = ErrCodeList.SEND_CONFIRM_EMAIL_FAIL.value

            # send notification to notificant
            if ret_code == ErrCodeList.SUCCES.value:
                if self.job_data["signerIdx"] == 0 and len(self.task_config["notificantEmail"]) > 0:
                    single_signer_email = None if len(
                        self.task_config["signerInfoList"]) > 1 else self.task_config["signerInfoList"][0]["emailAddr"]
                    mail_sender_obj = mail_sender.MailSender(self.email_config)
                    ret_code = mail_sender_obj.send_notificant_notify_mail(
                        self.task_config["notificantLocale"], self.task_config["notificantEmail"], self.job_data["taskID"], self.task_config["fileName"], single_signer_email)

                    if ret_code == ErrCodeList.SEND_EMAIL_FAIL.value:
                        ret_code = ErrCodeList.SEND_NOTIFY_EMAIL_FAIL.value
            else:
                try:
                    if self.job_data["signerIdx"] == 0 and len(self.task_config["notificantEmail"]) > 0:
                        single_signer_email = None if len(
                            self.task_config["signerInfoList"]) > 1 else self.task_config["signerInfoList"][0]["emailAddr"]
                        mail_sender_obj = mail_sender.MailSender(
                            self.email_config)
                        mail_sender_obj.send_notificant_error_mail(
                            self.task_config["notificantLocale"], self.task_config["notificantEmail"], self.job_data["taskID"], self.task_config["fileName"], single_signer_email)
                except BaseException as e:
                    logging.error(traceback.format_exc())

            # output results
            if ret_code == ErrCodeList.SUCCES.value:
                results.append({"name": "por", "bytes": por_data_bytes})

        except BaseException as e:
            logging.error(traceback.format_exc())
            ret_code = ErrCodeList.UNDEFINED_ERROR.value

        return ret_code, results if ret_code == ErrCodeList.SUCCES.value else [], None

    def __test_signed_pdf(self, decrypted_pdf):
        try:
            pdf_bytes = base64.b64decode(decrypted_pdf)

            # find latest EOF
            latest_eof_idx = pdf_bytes.rfind(EOF_MARKER.encode("utf-8"))

            if latest_eof_idx == -1:
                return False

            # parse metadata string
            metadata_str = pdf_bytes[latest_eof_idx +
                                     len(EOF_MARKER):].decode("utf-8", "ignore")
            metadata_str = "".join(metadata_str.split())

            # parse metadata key/value pairs
            metadata_info = {}
            metadata_list = metadata_str.split(";")
            for metadta in metadata_list:
                key_value = metadta.split("=")
                if len(key_value) == 2:
                    metadata_info[key_value[0]] = key_value[1]

            if "letsesign" in metadata_info and metadata_info["letsesign"] == "true":
                return True
            else:
                return False
        except BaseException as e:
            logging.error(traceback.format_exc())
            return False

    def __test_pdf_modifiable(self, signer_list, decrypted_pdf):
        try:
            pdf_tool_fields = []

            for signer in signer_list:
                pdf_tool_fields.append({
                    "emailAddr": "DUMMY_EMAIL",
                    "name": "DUMMY_NAME",
                    "locale": "en-US",
                    "fieldList": signer["fieldList"],
                    "signHint": False
                })

            dummy_pdf_b64 = pdf_tool_util.gen_preview_pdf(
                decrypted_pdf, pdf_tool_fields, None)

            if dummy_pdf_b64 is None:
                return False
            else:
                return True
        except BaseException as e:
            logging.error(traceback.format_exc())
            return True
