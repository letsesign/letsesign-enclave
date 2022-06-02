import json
import hmac
import base64
import logging
import datetime
import hashlib
import traceback

from asn1crypto import cms

from lib import crypto_util
from lib import libnsm_util
from lib import requests_util


AMZ_TARGET_DECRYPT = "TrentService.Decrypt"


def __extract_kms_region(kms_key_arn):
    return kms_key_arn.split(":")[3]


def __sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def __get_signature_key(key, date_stamp, region_name, service_name):
    kDate = __sign(("AWS4" + key).encode("utf-8"), date_stamp)
    kRegion = __sign(kDate, region_name)
    kService = __sign(kRegion, service_name)
    kSigning = __sign(kService, "aws4_request")

    return kSigning


def __exe_kms_post_request(aws_key_id, aws_key_secret, kms_region,  amz_target, request_data):
    service = "kms"
    api_host = f"kms.{kms_region}.amazonaws.com"
    api_endpoint = f"https://kms.{kms_region}.amazonaws.com/"
    algorithm = "AWS4-HMAC-SHA256"
    content_type = "application/x-amz-json-1.1"
    current_time = datetime.datetime.utcnow()

    amz_date = current_time.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = current_time.strftime("%Y%m%d")
    credential_scope = f"{date_stamp}/{kms_region}/{service}/aws4_request"
    signed_headers = "content-type;host;x-amz-date;x-amz-target"

    canonical_headers = f"content-type:{content_type}\nhost:{api_host}\nx-amz-date:{amz_date}\nx-amz-target:{amz_target}\n"
    canonical_request = f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{hashlib.sha256(request_data.encode('utf-8')).hexdigest()}"
    string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    signing_key = __get_signature_key(
        aws_key_secret, date_stamp, kms_region, service)
    signature = hmac.new(signing_key, string_to_sign.encode(
        "utf-8"), hashlib.sha256).hexdigest()

    authorization_header = f"{algorithm} Credential={aws_key_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    headers = {
        "X-Amz-Target": amz_target,
        "X-Amz-Date": amz_date,
        "Content-Type": content_type,
        "Authorization": authorization_header
    }

    response = requests_util.gen_requests_session().post(
        api_endpoint, headers=headers, data=request_data, timeout=10)
    response.raise_for_status()

    return response.json()


def decrypt_data(aws_key_id, aws_key_secret, kms_key_arn, encrypted_data):
    try:
        kms_region = __extract_kms_region(kms_key_arn)
        prv_key_pem = crypto_util.gen_rsa_key(2048)
        pub_key_der = crypto_util.derive_pub_key(prv_key_pem, False)
        attest_doc_bytes = libnsm_util.nsm_lib_get_attestation_doc(
            None, pub_key_der)

        request_data = {
            "KeyId": kms_key_arn,
            "EncryptionAlgorithm": "RSAES_OAEP_SHA_256",
            "CiphertextBlob": encrypted_data,
            "Recipient": {
                "KeyEncryptionAlgorithm": "RSAES_OAEP_SHA_256",
                "AttestationDocument": base64.b64encode(attest_doc_bytes).decode("utf-8")
            }
        }

        response = __exe_kms_post_request(
            aws_key_id, aws_key_secret, kms_region, AMZ_TARGET_DECRYPT, json.dumps(request_data, ensure_ascii=False, separators=(',', ':')))

        content_info_obj = cms.ContentInfo.load(
            base64.b64decode(response["CiphertextForRecipient"]))
        enveloped_data_obj = content_info_obj['content']
        encrytped_key_bytes = enveloped_data_obj['recipient_infos'][0].chosen['encrypted_key'].native
        iv_bytes = enveloped_data_obj['encrypted_content_info']['content_encryption_algorithm'].encryption_iv
        encrypted_content_bytes = enveloped_data_obj['encrypted_content_info']['encrypted_content'].native

        decrypted_key_bytes = crypto_util.rsa_decrypt_data(
            prv_key_pem, encrytped_key_bytes)
        decrypted_data_bytes = crypto_util.aes_cbc_decrypt_data(
            decrypted_key_bytes, iv_bytes, encrypted_content_bytes)

        return decrypted_data_bytes
    except BaseException as e:
        logging.error(traceback.format_exc())

    return None
