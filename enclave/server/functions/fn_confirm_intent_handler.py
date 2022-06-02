import time
import base64
import logging
import hashlib
import traceback

import cbor2
import twilio
from twilio.rest import TwilioHttpClient, Client

from lib import mail_sender
from lib import params_checker
from lib import attest_doc_util
from lib.costant_data import JobNameList
from lib.err_code_util import ErrCodeList
from functions.fn_base_handler import BaseFunctionHandler


class CustomTwilioHttpClient(TwilioHttpClient):
    def __init__(self):
        TwilioHttpClient.__init__(self, timeout=5)


class ConfirmIntentHandler(BaseFunctionHandler):
    def __init__(self, job_data):
        BaseFunctionHandler.__init__(
            self, job_data, params_checker.confirm_intent_job_schema)

    def do_job_internal(self):
        ret_code = ErrCodeList.UNDEFINED_ERROR.value
        results = []
        twilio_verification_sid = None

        try:
            # verify POR attestation document
            por_data_bytes = base64.b64decode(self.job_data["por"])
            por_data_hash = hashlib.sha256(por_data_bytes).hexdigest()
            por_data = cbor2.loads(por_data_bytes)
            is_valid_attest_document, fn_name, hash_list, timestamp = attest_doc_util.check_attest_document(
                base64.b64decode(self.job_data["porAttestDocument"]))

            if is_valid_attest_document and fn_name == JobNameList.SEND_REQ and por_data_hash == hash_list[0]["hash"]:
                ret_code = ErrCodeList.SUCCES.value
                logging.debug("pass POR validation")
            else:
                ret_code = ErrCodeList.INVALID_SIGNER_POR.value

            # check POR contents
            if ret_code == ErrCodeList.SUCCES.value:
                secret_hash = hashlib.sha256(
                    self.job_data["secret"].encode("utf-8")).hexdigest()
                if secret_hash != por_data["secretHash"] or self.payload_hash != por_data["payloadHash"]:
                    ret_code = ErrCodeList.MISMATCH_SIGNER_POR_CONTENT.value
                else:
                    logging.debug("pass POR content validation")

            # check signer phone
            if ret_code == ErrCodeList.SUCCES.value and por_data["phoneRequired"]:
                target_signer_info = self.task_config["signerInfoList"][por_data["signerIdx"]]

                if "twilioVerificationSID" in self.job_data and "twilioVerificationPIN" in self.job_data:
                    ret_code = self.__check_signer_phone(
                        self.twilio_config, self.job_data["twilioVerificationSID"], target_signer_info["phoneNumber"], self.job_data["twilioVerificationPIN"])
                else:
                    ret_code, twilio_verification_sid = self.__send_verificatoin_sms(
                        self.twilio_config, target_signer_info["phoneNumber"])

                    if ret_code == ErrCodeList.SUCCES.value:
                        ret_code = ErrCodeList.WAITING_VERIFICATION_PIN_CODE.value

            # generate POI
            if ret_code == ErrCodeList.SUCCES.value:
                result = {
                    "payloadHash": por_data["payloadHash"],
                    "signerIdx": por_data["signerIdx"],
                    "ipAddress": self.job_data["ipAddress"],
                    "porTime": timestamp
                }

                logging.debug("POI data has been generated")

                results.append({"name": "poi", "bytes": cbor2.dumps(result)})

            # send signed event mail
            if ret_code == ErrCodeList.SUCCES.value:
                if len(self.task_config["notificantEmail"]) > 0:
                    if len(self.task_config["signerInfoList"]) > 1:
                        signer_list = [{
                            "name": self.task_config["signerInfoList"][por_data["signerIdx"]]["name"],
                            "signingTime": int(time.time())
                        }]
                        mail_sender_obj = mail_sender.MailSender(
                            self.email_config)
                        mail_sender_obj.send_notificant_signed_event_mail(
                            self.task_config["notificantLocale"], self.task_config["notificantEmail"], self.job_data["taskID"], self.task_config["fileName"], signer_list)
        except BaseException as e:
            logging.error(traceback.format_exc())
            ret_code = ErrCodeList.UNDEFINED_ERROR.value

        return ret_code, results if ret_code == ErrCodeList.SUCCES.value else [], twilio_verification_sid

    def __check_signer_phone(self, twilio_config, verification_sid, phone_number, pin_code):
        try:
            custom_client = CustomTwilioHttpClient()
            client = Client(
                twilio_config["apiSID"], twilio_config["apiSecret"], http_client=custom_client)

            verification_result = client.verify.services(twilio_config["serviceSID"]).verification_checks.create(
                verification_sid=verification_sid, code=pin_code)

            if verification_result.to == phone_number and verification_result.channel == "sms" and verification_result.status == "approved":
                return ErrCodeList.SUCCES.value
        except twilio.base.exceptions.TwilioRestException as e:
            logging.error(traceback.format_exc())
            if e.code == 20003 or e.code == 20404:
                return ErrCodeList.INVALID_TWILIO_CREDENTAIL.value
        except BaseException as e:
            logging.error(traceback.format_exc())

        return ErrCodeList.CHECK_PHONE_FAIL.value

    def __send_verificatoin_sms(self, twilio_config, phone_number):
        try:
            custom_client = CustomTwilioHttpClient()
            client = Client(
                twilio_config["apiSID"], twilio_config["apiSecret"], http_client=custom_client)

            service = client.verify.services(
                twilio_config["serviceSID"]).fetch()

            if service.friendly_name == "Let's eSign" and service.code_length == 6:
                verification_result = client.verify.services(
                    twilio_config["serviceSID"]).verifications.create(to=phone_number, channel="sms")

                return ErrCodeList.SUCCES.value, verification_result.sid
            else:
                return ErrCodeList.INVALID_TWILIO_SETTING.value, None
        except twilio.base.exceptions.TwilioRestException as e:
            logging.error(traceback.format_exc())
            if e.code == 20003 or e.code == 20404:
                return ErrCodeList.INVALID_TWILIO_CREDENTAIL.value, None
        except BaseException as e:
            logging.error(traceback.format_exc())

        return ErrCodeList.SEND_SMS_FAIL.value, None
