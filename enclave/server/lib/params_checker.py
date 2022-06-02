import logging

from jsonschema import validate, exceptions
from jsonschema._format import draft7_format_checker

# json schema for getJob parameters
get_job_params_schema = {
    "type": "object",
    "properties": {
        "session": {"type": "string", "minLength": 1, "maxLength": 256},
        "jobName": {"type": "string", "minLength": 1, "maxLength": 256},
        "jobData": {
            "type": "object",
            "properties": {}
        }
    },
    "required": ["session", "jobName", "jobData"]
}

# json schema for domain setting
task_domain_setting_schema = {
    "type": "object",
    "properties": {
        "rootDomain": {"type": "string", "minLength": 1, "maxLength": 512},
        "signerAppURL": {"type": "string", "minLength": 1, "maxLength": 1024},
        "enhancedPrivacy": {"type": "boolean"},
        "kmsConfig": {
            "type": "object",
                    "properties": {
                        "kmsKeyARN": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 256,
                            "pattern": "^arn:aws:kms:us-east-1:"
                        }
                    },
            "required": ["kmsKeyARN"]
        },
        "emailServiceProvider": {"type": "string", "enum": ["ses", "sg"]},
        "emailServiceDomain": {"type": "string", "minLength": 1, "maxLength": 512}
    },
    "required": ["rootDomain", "signerAppURL", "enhancedPrivacy", "kmsConfig", "emailServiceProvider", "emailServiceDomain"]
}

# json schema for task template info
task_template_info_schema = {
    "type": "object",
    "properties": {
        "signerList": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "signerEmail": {"type": "string", "maxLength": 256},
                    "fieldList": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number", "minimum": 0, "maximum": 9999},
                                "y": {"type": "number", "minimum": 0, "maximum": 9999},
                                "height": {"type": "number", "minimum": 0, "maximum": 9999},
                                "pageNo": {"type": "number", "minimum": 0, "maximum": 9999},
                                "type": {"type": "number", "minimum": 0, "maximum": 99}
                            },
                            "required": ["x", "y", "height", "pageNo", "type"]
                        }
                    }

                },
                "required": ["fieldList"]
            }
        }
    },
    "required": ["signerList"]
}

# json schema for task encrypted data
task_encrypted_data_schema = {
    "type": "object",
    "properties": {
        "encryptedDataKey": {"type": "string", "minLength": 1, "maxLength": 1024},
        "dataIV": {"type": "string", "minLength": 1, "maxLength": 256},
        "encryptedData": {"type": "string", "minLength": 1}
    },
    "required": ["encryptedDataKey", "dataIV", "encryptedData"]
}

# json schema for task signer info
task_signer_info_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 256},
        "emailAddr": {"type": "string", "minLength": 1, "maxLength": 256, "pattern": "^[\\w\\.\\+\\-]+\\@[\\w\\.\\+\\-]+\\.[a-z]{2,3}$"},
        "phoneNumber": {
            "type": "string",
            "pattern": "^$|^\\+[1-9]\\d{1,14}$"
        },
        "locale": {"type": "string", "minLength": 1, "maxLength": 256}
    },
    "required": ["emailAddr", "name", "locale"]
}

# json schema for decrypted task config
task_decrypted_task_config_schema = {
    "type": "object",
    "properties": {
        "taskConfig": {
            "type": "object",
            "properties": {
                "fileName": {"type": "string", "minLength": 1, "maxLength": 256},
                "senderMsg": {"type": "string", "maxLength": 2048},
                "notificantEmail": {
                    "type": "string", "maxLength": 256,
                    "pattern": "^$|^[\\w\\.\\+\\-]+\\@[\\w\\.\\+\\-]+\\.[a-z]{2,3}$"
                },
                "notificantLocale": {"type": "string", "minLength": 1, "maxLength": 256},
                "signerInfoList": {
                    "type": "array",
                    "minItems": 1,
                    "items": task_signer_info_schema
                }
            },
            "required": ["fileName", "senderMsg", "notificantEmail", "notificantLocale", "signerInfoList"]
        }
    },
    "required": ["taskConfig"]
}

# json schema for decrypted email config
task_decrypted_email_config_schema = {
    "type": "object",
    "properties": {
        "emailConfig": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "serviceProvider": {"type": "string", "enum": ["ses"]},
                        "sesSMTPUsername": {"type": "string", "minLength": 1, "maxLength": 256},
                        "sesSMTPPassword": {"type": "string", "minLength": 1, "maxLength": 256},
                        "sesDomain": {"type": "string", "minLength": 1, "maxLength": 256}
                    },
                    "required": ["serviceProvider", "sesSMTPUsername", "sesSMTPPassword", "sesDomain"]
                },
                {
                    "type": "object",
                    "properties": {
                        "serviceProvider": {"type": "string", "enum": ["sg"]},
                        "sgSecret": {"type": "string", "minLength": 1, "maxLength": 256},
                        "sgDomain": {"type": "string", "minLength": 1, "maxLength": 256}
                    },
                    "required": ["serviceProvider", "sgSecret", "sgDomain"]
                }
            ]
        },
        "bearerSecret": {"type": "string", "minLength": 1, "maxLength": 256}
    },
    "required": ["emailConfig", "bearerSecret"]
}

# json schema for task twilio config
task_decrypted_twilio_config_schema = {
    "type": "object",
    "properties": {
        "twilioConfig": {
            "type": "object",
            "properties": {
                "apiSID": {"type": "string", "minLength": 1, "maxLength": 256},
                "apiSecret": {"type": "string", "minLength": 1, "maxLength": 256},
                "serviceSID": {"type": "string", "minLength": 1, "maxLength": 256}
            },
            "required": ["apiSID", "apiSecret", "serviceSID"]
        },
        "bearerSecret": {"type": "string", "minLength": 1, "maxLength": 256}
    },
    "required": ["twilioConfig", "bearerSecret"]
}

# json schema for task binding data
task_decrypted_binding_data_schema = {
    "type": "object",
    "properties": {
        "bindingData": {
            "type": "object",
            "properties": {
                "inOrder": {"type": "boolean"},
                "taskConfigHash": {"type": "string", "minLength": 1, "maxLength": 256},
                "templateInfoHash": {"type": "string", "minLength": 1, "maxLength": 256},
                "templateDataHash": {"type": "string", "minLength": 1, "maxLength": 256},
                "accessKey": {"type": "string", "minLength": 1, "maxLength": 256},
                "bearerSecret": {"type": "string", "minLength": 1, "maxLength": 256}
            },
            "required": ["inOrder", "taskConfigHash", "templateInfoHash", "templateDataHash", "accessKey", "bearerSecret"]
        }
    },
    "required": ["bindingData"]
}

# json schema for task payload
task_payload_schema = {
    "type": "object",
    "properties": {
        "publicTaskInfo": {
            "type": "object",
            "properties": {
                "domainSetting": task_domain_setting_schema,
                "inOrder": {"type": "boolean"},
                "templateInfo": task_template_info_schema
            },
            "required": ["domainSetting", "inOrder", "templateInfo"]
        },
        "privateTaskInfo": {
            "type": "object",
            "properties": {
                "encryptedTaskConfig": task_encrypted_data_schema,
                "encryptedTemplateData": task_encrypted_data_schema,
                "encryptedEmailConfig": task_encrypted_data_schema,
                "encryptedTwilioConfig": task_encrypted_data_schema,
                "encryptedBindingData": task_encrypted_data_schema
            },
            "required": ["encryptedTaskConfig", "encryptedTemplateData", "encryptedEmailConfig", "encryptedBindingData"]
        }
    },
    "required": ["publicTaskInfo", "privateTaskInfo"]
}

# json schema for sendReq job
send_req_job_schema = {
    "type": "object",
    "properties": {
        "taskID": {"type": "string", "minLength": 1, "maxLength": 256},
        "subTaskID": {"type": "string", "minLength": 1, "maxLength": 256},
        "taskPayload": task_payload_schema,
        "signerIdx": {"type": "number", "minimum": 0, "maximum": 999},
        "taskPassword": {"type": "string", "minLength": 1, "maxLength": 256},
        "extraData": {
            "type": "object",
            "properties": {
                "kmsKeyID": {"type": "string", "minLength": 1, "maxLength": 256},
                "kmsKeySecret": {"type": "string", "minLength": 1, "maxLength": 256},
                "apiVersion": {"type": "string", "minLength": 1, "maxLength": 1024},
                "auxData": {"type": "string", "maxLength": 1024}
            },
            "required": ["kmsKeyID", "kmsKeySecret", "apiVersion", "auxData"]
        }
    },
    "required": ["taskPassword", "taskID", "subTaskID", "taskPayload", "signerIdx", "extraData"]
}

# json schema for confirmIntent data
confirm_intent_job_schema = {
    "type": "object",
    "properties": {
        "taskID": {"type": "string", "minLength": 1, "maxLength": 256},
        "subTaskID": {"type": "string", "minLength": 1, "maxLength": 256},
        "taskPayload": task_payload_schema,
        "secret": {"type": "string", "minLength": 1, "maxLength": 1024},
        "ipAddress": {"type": "string", "format": "ipv4"},
        "por": {"type": "string", "minLength": 1, "maxLength": 1024},
        "porAttestDocument": {"type": "string", "minLength": 1, "maxLength": 10240},
        "twilioVerificationSID": {"type": "string", "minLength": 1, "maxLength": 256},
        "twilioVerificationPIN": {"type": "string", "minLength": 1, "maxLength": 256},
        "extraData": {
            "type": "object",
            "properties": {
                "kmsKeyID": {"type": "string", "minLength": 1, "maxLength": 256},
                "kmsKeySecret": {"type": "string", "minLength": 1, "maxLength": 256},
            },
            "required": ["kmsKeyID", "kmsKeySecret"]
        }
    },
    "required": ["taskID", "subTaskID", "taskPayload", "secret", "ipAddress", "por", "porAttestDocument", "extraData"]
}

# json schema for attachEsig data
attach_esig_data_schema = {
    "type": "object",
    "properties": {
        "taskID": {"type": "string", "minLength": 1, "maxLength": 256},
        "subTaskID": {"type": "string", "minLength": 1, "maxLength": 256},
        "taskPayload": task_payload_schema,
        "proofList": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "poi": {"type": "string", "minLength": 1, "maxLength": 1024},
                    "poiAttestDocument": {"type": "string", "minLength": 1, "maxLength": 10240}
                },
                "required": ["poi", "poiAttestDocument"]
            }
        },
        "taskPassword": {"type": "string", "minLength": 1, "maxLength": 256},
        "extraData": {
            "type": "object",
            "properties": {
                "kmsKeyID": {"type": "string", "minLength": 1, "maxLength": 256},
                "kmsKeySecret": {"type": "string", "minLength": 1, "maxLength": 256},
                "apiVersion": {"type": "string", "minLength": 1, "maxLength": 1024},
                "auxData": {"type": "string", "maxLength": 1024}
            },
            "required": ["kmsKeyID", "kmsKeySecret", "apiVersion", "auxData"]
        }
    },
    "required": ["taskPassword", "taskID", "subTaskID", "taskPayload", "proofList", "extraData"]
}


def verify_param_with_schema(params, schema):
    try:
        validate(instance=params, schema=schema,
                 format_checker=draft7_format_checker)
        return True
    except exceptions.ValidationError as e:
        logging.error(e.message)
        return False
