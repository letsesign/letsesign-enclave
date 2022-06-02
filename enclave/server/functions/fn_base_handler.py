import abc
import json
import hashlib
import logging
import traceback

from lib import params_checker
from lib import encryption_util
from lib.err_code_util import ErrCodeList


class BaseFunctionHandler(metaclass=abc.ABCMeta):
    def __init__(self, job_data, job_param_schema):
        self.job_data = job_data
        self.job_param_schema = job_param_schema
        self.payload_hash = None
        self.binding_data = None
        self.task_config = None
        self.template_data = None
        self.email_config = None
        self.twilio_config = None

    def do_job(self):
        ret_code = ErrCodeList.UNDEFINED_ERROR.value
        results = []
        extra_output = None

        try:
            # check job data
            if params_checker.verify_param_with_schema(self.job_data, self.job_param_schema):
                ret_code = ErrCodeList.SUCCES.value
                self.payload_hash = hashlib.sha256(json.dumps(
                    self.job_data["taskPayload"], ensure_ascii=False, separators=(',', ':')).encode("utf-8")).hexdigest()

                logging.debug("pass job parameter verification")
                logging.debug(f"payload hash: {self.payload_hash}")
            else:
                ret_code = ErrCodeList.INVALID_PARAM.value

            # decrypt private task info
            if ret_code == ErrCodeList.SUCCES.value:
                ret_code, binding_data, task_config, template_data, email_config, twilio_config = encryption_util.decrypt_private_task_info(
                    self.job_data["taskPayload"], self.job_data["extraData"]["kmsKeyID"], self.job_data["extraData"]["kmsKeySecret"])

                if ret_code == ErrCodeList.SUCCES.value:
                    self.binding_data = binding_data
                    self.task_config = task_config
                    self.template_data = template_data
                    self.email_config = email_config
                    self.twilio_config = twilio_config

            # do function job
            if ret_code == ErrCodeList.SUCCES.value:
                ret_code, results, extra_output = self.do_job_internal()
        except BaseException as e:
            logging.error(traceback.format_exc())
            ret_code = ErrCodeList.UNDEFINED_ERROR.value

        return ret_code, results, extra_output

    @abc.abstractmethod
    def do_job_internal(self):
        pass
