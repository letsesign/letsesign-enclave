import io
import os
import json
import base64
import hashlib
import logging
import traceback
from datetime import datetime

import cbor2
import pyzipper

from lib import crypto_util
from lib import mail_sender
from lib import pdf_tool_util
from lib import params_checker
from lib import attest_doc_util
from lib.costant_data import JobNameList
from lib.err_code_util import ErrCodeList
from functions.fn_base_handler import BaseFunctionHandler


class AttachESigHandler(BaseFunctionHandler):
    def __init__(self, job_data):
        BaseFunctionHandler.__init__(
            self, job_data, params_checker.attach_esig_data_schema)

    def do_job_internal(self):
        ret_code = ErrCodeList.UNDEFINED_ERROR.value
        results = []

        try:
            pdf_tool_fields = []
            summary_data = {"signerList": [],
                            "magicNumber": None, "bindingDataHash": None}
            prev_signer_poi_time = 0

            # check length of proof list
            if len(self.job_data["proofList"]) == len(self.task_config["signerInfoList"]):
                ret_code = ErrCodeList.SUCCES.value
            else:
                ret_code = ErrCodeList.MISMATCH_PROOF_LIST_LENGTH.value

            # check signer POI
            if ret_code == ErrCodeList.SUCCES.value:
                for signer_idx in range(len(self.task_config["signerInfoList"])):
                    logging.debug(f"checking signer intent: {signer_idx}")

                    poi_data_bytes = base64.b64decode(
                        self.job_data["proofList"][signer_idx]["poi"])
                    poi_data_hash = hashlib.sha256(poi_data_bytes).hexdigest()
                    poi_data = cbor2.loads(poi_data_bytes)
                    is_valid_attest_document, fn_name, hash_list, timestamp = attest_doc_util.check_attest_document(
                        base64.b64decode(self.job_data["proofList"][signer_idx]["poiAttestDocument"]))

                    # check POI correctness
                    if not is_valid_attest_document or fn_name != JobNameList.CONFIRM_INTENT or poi_data_hash != hash_list[0]["hash"]:
                        ret_code = ErrCodeList.INVALID_SIGNER_POI.value
                        break

                    logging.debug("pass POI validation")

                    # check POI content
                    if poi_data["payloadHash"] != self.payload_hash or poi_data["signerIdx"] != signer_idx or poi_data["porTime"] > timestamp:
                        ret_code = ErrCodeList.MISMATCH_SIGNER_POI_CONTENT.value
                        break

                    logging.debug("pass POI content validation")

                    # check the time sequence if sign with inorder
                    if self.job_data["taskPayload"]["publicTaskInfo"]["inOrder"]:
                        if poi_data["porTime"] < prev_signer_poi_time:
                            ret_code = ErrCodeList.INVALID_SIGN_TIME_ORDER.value
                            break
                        else:
                            logging.debug("pass signing order check")

                    prev_signer_poi_time = timestamp

                    # prepare pdf-tool parameters
                    current_signer = self.task_config["signerInfoList"][signer_idx]
                    signer_field = {
                        "emailAddr": current_signer["emailAddr"],
                        "name": current_signer["name"],
                        "locale": current_signer["locale"],
                        "fieldList": self.job_data["taskPayload"]["publicTaskInfo"]["templateInfo"]["signerList"][signer_idx]["fieldList"],
                        "signingTime": datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y/%m/%d (UTC)")
                    }
                    summary_signer_item = {
                        "name": signer_field["name"],
                        "emailAddr": signer_field["emailAddr"],
                        "ipAddress": poi_data["ipAddress"],
                        "signingTime": int(timestamp / 1000)
                    }

                    if current_signer.get("phoneNumber"):
                        signer_field["phoneNumber"] = current_signer["phoneNumber"]
                        summary_signer_item["phoneNumber"] = signer_field["phoneNumber"]

                    pdf_tool_fields.append(signer_field)
                    summary_data["signerList"].append(summary_signer_item)

            # generate eSignature PDF
            if ret_code == ErrCodeList.SUCCES.value:
                magic_number = crypto_util.gen_random_bytes(32).hex()

                esig_pdf_b64 = pdf_tool_util.gen_signed_pdf(
                    self.template_data, pdf_tool_fields, magic_number)

                if esig_pdf_b64 is None:
                    ret_code = ErrCodeList.GENERATE_SIGNING_PDF_FAIL.value
                else:
                    logging.debug("signing PDF has been generated")

                    summary_data["magicNumber"] = magic_number
                    summary_data["bindingDataHash"] = hashlib.sha256(json.dumps({
                        "inOrder": self.binding_data["inOrder"],
                        "taskConfigHash": self.binding_data["taskConfigHash"],
                        "templateInfoHash": self.binding_data["templateInfoHash"],
                        "templateDataHash": self.binding_data["templateDataHash"]
                    }, ensure_ascii=False, separators=(',', ':')).encode("utf-8")).hexdigest()

                    summary_data_bytes = json.dumps(
                        summary_data, ensure_ascii=False, separators=(',', ':')).encode("utf-8")

                    results.append(
                        {"name": "esigPDF", "bytes": base64.b64decode(esig_pdf_b64)})
                    results.append(
                        {"name": "summary", "bytes": summary_data_bytes})

        except BaseException as e:
            logging.error(traceback.format_exc())
            ret_code = ErrCodeList.UNDEFINED_ERROR.value

        return ret_code, results if ret_code == ErrCodeList.SUCCES.value else [], None

    def notify_result(self, results, attest_document_b64):
        try:
            summary_data = json.loads(base64.b64decode(results[1]["data"]))

            # generate spf file
            spf_file_bytes = self.__gen_spf_file(
                summary_data, attest_document_b64)

            # prepare zip file
            file_name_without_extension = os.path.splitext(
                self.task_config["fileName"])[0]
            zip_file_bytes = self.__gen_zip_file(file_name_without_extension, self.job_data["taskPassword"] if self.job_data[
                                                 "taskPayload"]["publicTaskInfo"]["domainSetting"]["enhancedPrivacy"] else None, results[0]["data"], spf_file_bytes)

            if len(summary_data["signerList"]) == 1:
                file_name_without_extension = f"{file_name_without_extension} ({summary_data['signerList'][0]['emailAddr']})"

            # send to notificant
            if len(self.task_config["notificantEmail"]) > 0:
                mail_sender_obj = mail_sender.MailSender(self.email_config)
                mail_sender_obj.send_notificant_final_mail(self.task_config["notificantLocale"], self.task_config["notificantEmail"], self.job_data[
                                                           "taskID"], self.task_config["fileName"], summary_data["signerList"], f"{file_name_without_extension}.zip", zip_file_bytes)

            # send to signers
            for signerIdx, signer in enumerate(summary_data["signerList"]):
                signer_locale = self.task_config["signerInfoList"][signerIdx]["locale"]
                mail_sender_obj = mail_sender.MailSender(self.email_config)
                mail_sender_obj.send_signer_final_mail(
                    signer_locale, signer["emailAddr"], self.job_data["taskID"], f"{file_name_without_extension}.zip", zip_file_bytes)

            return True
        except BaseException as e:
            logging.error(traceback.format_exc())

        return False

    def encrypt_result(self, results, attest_document_b64):
        try:
            iv_bytes = crypto_util.gen_random_bytes(16)
            summary_data = json.loads(base64.b64decode(results[1]["data"]))

            # generate spf file
            spf_file_bytes = self.__gen_spf_file(
                summary_data, attest_document_b64)

            # prepare zip file
            file_name_without_extension = os.path.splitext(
                self.task_config["fileName"])[0]
            zip_file_bytes = self.__gen_zip_file(
                file_name_without_extension, None, results[0]["data"], spf_file_bytes)

            # encrypt zip file
            encrypted_zip_bytes = crypto_util.aes_cbc_encrypt_data(
                base64.b64decode(self.binding_data["accessKey"]), iv_bytes, zip_file_bytes)

            if encrypted_zip_bytes is not None:
                return base64.b64encode(b"".join([iv_bytes, encrypted_zip_bytes])).decode("utf-8")
        except BaseException as e:
            logging.error(traceback.format_exc())

        return None

    def __gen_spf_file(self, summary_b64, attest_doc_b64):
        return json.dumps({
            "summary": summary_b64,
            "attestDoc": attest_doc_b64
        }, ensure_ascii=False, separators=(',', ':')).encode("utf-8")

    def __gen_zip_file(self, file_name, password, pdf_b64, spf_file_bytes):
        zip_buffer = io.BytesIO()

        with pyzipper.AESZipFile(zip_buffer, 'w', compression=pyzipper.ZIP_DEFLATED) as zip_file:
            if password:
                zip_file.setpassword(password.encode("utf-8"))
                zip_file.setencryption(pyzipper.WZ_AES, nbits=256)

            zip_file.writestr(f"{file_name}.pdf", base64.b64decode(pdf_b64))
            zip_file.writestr(f"{file_name}.spf", spf_file_bytes)

        return zip_buffer.getvalue()
