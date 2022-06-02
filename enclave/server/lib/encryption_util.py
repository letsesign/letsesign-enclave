import json
import base64
import hashlib
import logging
import traceback

from lib import kms_util
from lib import crypto_util
from lib import params_checker
from lib.err_code_util import ErrCodeList


def __decrypt_encrypted_data(kms_key_arn, encrypted_data_key, data_iv, encrypted_data, kms_key_id, kms_key_secret):
    ret_code = ErrCodeList.SUCCES.value
    decrypted_data_bytes = None

    # decrypt cipher key
    aes_key_bytes = kms_util.decrypt_data(
        kms_key_id, kms_key_secret, kms_key_arn, encrypted_data_key)

    if aes_key_bytes is None:
        ret_code = ErrCodeList.DECRYPT_PRIVATE_INFO_FAIL.value

    # decrypt encrypted data
    if ret_code == ErrCodeList.SUCCES.value:
        decrypted_data_bytes = crypto_util.aes_cbc_decrypt_data(
            aes_key_bytes, base64.b64decode(data_iv), base64.b64decode(encrypted_data))

        if decrypted_data_bytes is None:
            ret_code = ErrCodeList.DECRYPT_PRIVATE_INFO_FAIL.value

    return ret_code, decrypted_data_bytes


def __decrypt_binding_data(kms_key_arn, kms_key_id, kms_key_secret, encrypted_binding_data):
    binding_data = None
    ret_code, decrypted_data_bytes = __decrypt_encrypted_data(
        kms_key_arn, encrypted_binding_data["encryptedDataKey"], encrypted_binding_data["dataIV"], encrypted_binding_data["encryptedData"], kms_key_id, kms_key_secret)

    if ret_code == ErrCodeList.SUCCES.value:
        decrypted_binding_data = json.loads(decrypted_data_bytes)

        if not params_checker.verify_param_with_schema(decrypted_binding_data, params_checker.task_decrypted_binding_data_schema):
            ret_code = ErrCodeList.INVALID_PARAM.value

        if ret_code == ErrCodeList.SUCCES.value:
            binding_data = decrypted_binding_data["bindingData"]

    return ret_code, binding_data


def __decrypt_task_config(kms_key_arn, kms_key_id, kms_key_secret, encrypted_task_config):
    task_config = None
    ret_code, decrypted_data_bytes = __decrypt_encrypted_data(
        kms_key_arn, encrypted_task_config["encryptedDataKey"], encrypted_task_config["dataIV"], encrypted_task_config["encryptedData"], kms_key_id, kms_key_secret)

    if ret_code == ErrCodeList.SUCCES.value:
        decrypted_task_config = json.loads(decrypted_data_bytes)

        if not params_checker.verify_param_with_schema(decrypted_task_config, params_checker.task_decrypted_task_config_schema):
            ret_code = ErrCodeList.INVALID_PARAM.value

        if ret_code == ErrCodeList.SUCCES.value:
            task_config = decrypted_task_config["taskConfig"]

    return ret_code, task_config


def __decrypt_template_data(kms_key_arn, kms_key_id, kms_key_secret, encrypted_template_data):
    template_data = None
    ret_code, decrypted_data_bytes = __decrypt_encrypted_data(
        kms_key_arn, encrypted_template_data["encryptedDataKey"], encrypted_template_data["dataIV"], encrypted_template_data["encryptedData"], kms_key_id, kms_key_secret)

    if ret_code == ErrCodeList.SUCCES.value:
        template_data = base64.b64encode(decrypted_data_bytes).decode("utf-8")

    return ret_code, template_data


def __decrypt_encrypted_email_config(kms_key_arn, kms_key_id, kms_key_secret, encrypted_email_config, email_service_provider, email_service_domain, bearerSecret):
    email_config = None
    ret_code, decrypted_data_bytes = __decrypt_encrypted_data(
        kms_key_arn, encrypted_email_config["encryptedDataKey"], encrypted_email_config["dataIV"], encrypted_email_config["encryptedData"], kms_key_id, kms_key_secret)

    if ret_code == ErrCodeList.SUCCES.value:
        decrypted_email_config = json.loads(decrypted_data_bytes)

        if not params_checker.verify_param_with_schema(decrypted_email_config, params_checker.task_decrypted_email_config_schema):
            ret_code = ErrCodeList.INVALID_PARAM.value

        if ret_code == ErrCodeList.SUCCES.value:
            if decrypted_email_config["emailConfig"]["serviceProvider"] != email_service_provider:
                logging.error("mismatch email service provider")
                ret_code = ErrCodeList.MISMATCH_EMAIL_CONFIG.value

        if ret_code == ErrCodeList.SUCCES.value:
            if decrypted_email_config["emailConfig"]["serviceProvider"] == "ses":
                if decrypted_email_config["emailConfig"]["sesDomain"] != email_service_domain:
                    logging.error(
                        "mismatch email service domain in email config")
                    ret_code = ErrCodeList.MISMATCH_EMAIL_CONFIG.value
            elif decrypted_email_config["emailConfig"]["serviceProvider"] == "sg":
                if decrypted_email_config["emailConfig"]["sgDomain"] != email_service_domain:
                    logging.error(
                        "mismatch email service domain in email config")
                    ret_code = ErrCodeList.MISMATCH_EMAIL_CONFIG.value
            else:
                logging.error("unsupported email service provider")
                ret_code = ErrCodeList.INVALID_PARAM.value

        if ret_code == ErrCodeList.SUCCES.value:
            if decrypted_email_config["bearerSecret"] != bearerSecret:
                ret_code = ErrCodeList.MISMATCH_BEARERSECRET.value

        if ret_code == ErrCodeList.SUCCES.value:
            email_config = decrypted_email_config["emailConfig"]

    return ret_code, email_config


def __decrypt_encrypted_twilio_config(kms_key_arn, kms_key_id, kms_key_secret, encrypted_twilio_config, bearerSecret):
    twilio_config = None
    ret_code, decrypted_data_bytes = __decrypt_encrypted_data(
        kms_key_arn, encrypted_twilio_config["encryptedDataKey"], encrypted_twilio_config["dataIV"], encrypted_twilio_config["encryptedData"], kms_key_id, kms_key_secret)

    if ret_code == ErrCodeList.SUCCES.value:
        decrypted_twilio_config = json.loads(decrypted_data_bytes)

        if not params_checker.verify_param_with_schema(decrypted_twilio_config, params_checker.task_decrypted_twilio_config_schema):
            ret_code = ErrCodeList.INVALID_PARAM.value

        if ret_code == ErrCodeList.SUCCES.value:
            if decrypted_twilio_config["bearerSecret"] != bearerSecret:
                ret_code = ErrCodeList.MISMATCH_BEARERSECRET.value

        if ret_code == ErrCodeList.SUCCES.value:
            twilio_config = decrypted_twilio_config["twilioConfig"]

    return ret_code, twilio_config


def decrypt_private_task_info(task_payload, kms_key_id, kms_key_secret):
    try:
        ret_code = ErrCodeList.DECRYPT_PRIVATE_INFO_FAIL.value
        binding_data = None
        template_data = None
        task_config = None
        email_config = None
        twilio_config = None
        tmp_binding_data = None
        tmp_task_config = None
        tmp_template_data = None
        tmp_email_config = None
        tmp_twilio_config = None

        # decrypt binding data
        ret_code, tmp_binding_data = __decrypt_binding_data(
            task_payload["publicTaskInfo"]["domainSetting"]["kmsConfig"]["kmsKeyARN"], kms_key_id, kms_key_secret, task_payload["privateTaskInfo"]["encryptedBindingData"])

        # check inorder option
        if ret_code == ErrCodeList.SUCCES.value:
            if task_payload["publicTaskInfo"]["inOrder"] != tmp_binding_data["inOrder"]:
                ret_code = ErrCodeList.MISMATCH_INORDER_OPTION.value

        # check template info hash
        if ret_code == ErrCodeList.SUCCES.value:
            template_info_hash = hashlib.sha256(json.dumps(
                task_payload["publicTaskInfo"]["templateInfo"], ensure_ascii=False, separators=(',', ':')).encode("utf-8")).hexdigest()
            if template_info_hash != tmp_binding_data["templateInfoHash"]:
                ret_code = ErrCodeList.MISMATCH_TEMPLATE_INFO_HASH.value

        # decrypt task config
        if ret_code == ErrCodeList.SUCCES.value:
            ret_code, tmp_task_config = __decrypt_task_config(
                task_payload["publicTaskInfo"]["domainSetting"]["kmsConfig"]["kmsKeyARN"], kms_key_id, kms_key_secret, task_payload["privateTaskInfo"]["encryptedTaskConfig"])

        # check task config hash
        if ret_code == ErrCodeList.SUCCES.value:
            task_config_hash = hashlib.sha256(json.dumps(
                tmp_task_config, ensure_ascii=False, separators=(',', ':')).encode("utf-8")).hexdigest()
            if task_config_hash != tmp_binding_data["taskConfigHash"]:
                ret_code = ErrCodeList.MISMATCH_TASK_CONFIG_HASH.value

        # decrypt template data
        if ret_code == ErrCodeList.SUCCES.value:
            ret_code, tmp_template_data = __decrypt_template_data(
                task_payload["publicTaskInfo"]["domainSetting"]["kmsConfig"]["kmsKeyARN"], kms_key_id, kms_key_secret, task_payload["privateTaskInfo"]["encryptedTemplateData"])

        # check template data hash
        if ret_code == ErrCodeList.SUCCES.value:
            template_data_hash = hashlib.sha256(
                base64.b64decode(tmp_template_data)).hexdigest()
            if template_data_hash != tmp_binding_data["templateDataHash"]:
                ret_code = ErrCodeList.MISMATCH_TEMPLATE_DATA_HASH.value

        # decrypt email config
        if ret_code == ErrCodeList.SUCCES.value:
            ret_code, tmp_email_config = __decrypt_encrypted_email_config(task_payload["publicTaskInfo"]["domainSetting"]["kmsConfig"]["kmsKeyARN"], kms_key_id, kms_key_secret, task_payload["privateTaskInfo"][
                                                                          "encryptedEmailConfig"], task_payload["publicTaskInfo"]["domainSetting"]["emailServiceProvider"], task_payload["publicTaskInfo"]["domainSetting"]["emailServiceDomain"], tmp_binding_data["bearerSecret"])

        # decrypt twilio config
        if ret_code == ErrCodeList.SUCCES.value and "encryptedTwilioConfig" in task_payload["privateTaskInfo"]:
            ret_code, tmp_twilio_config = __decrypt_encrypted_twilio_config(
                task_payload["publicTaskInfo"]["domainSetting"]["kmsConfig"]["kmsKeyARN"], kms_key_id, kms_key_secret, task_payload["privateTaskInfo"]["encryptedTwilioConfig"], tmp_binding_data["bearerSecret"])

        if ret_code == ErrCodeList.SUCCES.value:
            binding_data = tmp_binding_data
            task_config = tmp_task_config
            template_data = tmp_template_data
            email_config = tmp_email_config

            if tmp_twilio_config:
                twilio_config = tmp_twilio_config

    except BaseException as e:
        logging.error(traceback.format_exc())
        ret_code = ErrCodeList.DECRYPT_PRIVATE_INFO_FAIL.value

    return ret_code, binding_data, task_config, template_data, email_config, twilio_config
