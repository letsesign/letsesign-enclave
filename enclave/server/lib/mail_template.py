import os
import html
from datetime import datetime

MAIL_TEMPLATE_FOLDER = "/server/resources/template"
BEGIN_SMS_NOTICE = "<!-- BEGIN SMS NOTICE -->"
END_SMS_NOTICE = "<!-- END SMS NOTICE -->"
BEGIN_SINGLE_SIGNER = "<!-- BEGIN SINGLE SIGNER -->"
END_SINGLE_SIGNER = "<!-- END SINGLE SIGNER -->"


def __load_mail_subject(locale, email_type):
    pre_tag = "<title>"
    post_tag = "</title>"

    # prepare locale file name
    locale_file_name = f"{MAIL_TEMPLATE_FOLDER}/{email_type}/{locale.lower()}_body.html"

    # use default locale if the locale file not exist
    if not os.path.exists(locale_file_name):
        locale_file_name = f"{MAIL_TEMPLATE_FOLDER}/{email_type}/en-us_body.html"

    with open(locale_file_name, "rt") as file:
        email_html = file.read()
        start_pos = email_html.index(pre_tag) + len(pre_tag)
        end_pos = email_html.index(post_tag, start_pos)

        return email_html[start_pos:end_pos]


def __load_mail_body(locale, email_type):
    # prepare locale file name
    locale_file_name = f"{MAIL_TEMPLATE_FOLDER}/{email_type}/{locale.lower()}_body.html"

    # use default locale if the locale file not exist
    if not os.path.exists(locale_file_name):
        locale_file_name = f"{MAIL_TEMPLATE_FOLDER}/{email_type}/en-us_body.html"

    with open(locale_file_name, "rt") as file:
        return file.read()


def __remove_msg_block(mail_body, begin_msg, end_msg):
    begin_index = mail_body.index(begin_msg)
    end_index = mail_body.index(end_msg)

    return mail_body[0:begin_index] + mail_body[end_index + len(end_msg):]


def get_error_mail_subject(locale, task_id):
    # load email subject
    mail_subject = __load_mail_subject(locale, "email_to_notificant_0")

    # fill task id
    mail_subject = mail_subject.replace("DUMMY_TASK_ID", task_id[-12:])

    return mail_subject


def get_error_mail_body(locale, file_name, single_signer_email):
    # load email body
    mail_body = __load_mail_body(locale, "email_to_notificant_0")

    # fill file name
    mail_body = mail_body.replace("DUMMY_FILE_NAME", file_name)

    # fill single signer email
    if single_signer_email:
        mail_body = mail_body.replace(
            "DUMMY_SIGNER_EMAIL", single_signer_email)
    else:
        mail_body = __remove_msg_block(
            mail_body, BEGIN_SINGLE_SIGNER, END_SINGLE_SIGNER)

    return mail_body


def get_notify_mail_subject(locale, task_id):
    # load email subject
    mail_subject = __load_mail_subject(locale, "email_to_notificant_1")

    # fill task id
    mail_subject = mail_subject.replace("DUMMY_TASK_ID", task_id[-12:])

    return mail_subject


def get_notify_mail_body(locale, file_name, single_signer_email):
    # load email body
    mail_body = __load_mail_body(locale, "email_to_notificant_1")

    # fill file name
    mail_body = mail_body.replace("DUMMY_FILE_NAME", file_name)

    # fill single signer email
    if single_signer_email:
        mail_body = mail_body.replace(
            "DUMMY_SIGNER_EMAIL", single_signer_email)
    else:
        mail_body = __remove_msg_block(
            mail_body, BEGIN_SINGLE_SIGNER, END_SINGLE_SIGNER)

    return mail_body


def get_confirm_mail_subject(locale, task_id):
    # load email subject
    mail_subject = __load_mail_subject(locale, "email_to_signer_1")

    # fill task id
    mail_subject = mail_subject.replace("DUMMY_TASK_ID", task_id[-12:])

    return mail_subject


def get_confirm_mail_body(locale, sender, signer_name, custom_message, confirm_link, signer_phone):
    # load email body
    mail_body = __load_mail_body(locale, "email_to_signer_1")

    # fill signer name
    mail_body = mail_body.replace("DUMMY_SIGNER_NAME", signer_name)

    # fill sender
    mail_body = mail_body.replace("DUMMY_SENDER", sender)

    # fill custom message
    mail_body = mail_body.replace("DUMMY_CUSTOM_MESSAGE", html.escape(
        custom_message).replace("\n", "<br>"))

    # fill confirm link
    mail_body = mail_body.replace("DUMMY_SIGNER_CONFIRM_LINK", confirm_link)

    # set sms notice
    if signer_phone:
        mail_body = mail_body.replace("DUMMY_SIGNER_PHONE", signer_phone)
    else:
        mail_body = __remove_msg_block(
            mail_body, BEGIN_SMS_NOTICE, END_SMS_NOTICE)

    return mail_body


def get_signed_event_mail_subject(locale, task_id):
    # load email subject
    mail_subject = __load_mail_subject(locale, "email_to_notificant_2")

    # fill task id
    mail_subject = mail_subject.replace("DUMMY_TASK_ID", task_id[-12:])

    return mail_subject


def get_signed_event_mail_body(locale, file_name, signer_list):
    # load email body
    mail_body = __load_mail_body(locale, "email_to_notificant_2")

    # fill file name
    mail_body = mail_body.replace("DUMMY_FILE_NAME", file_name)

    # fill signers
    signer_list_str = ""
    for signer in signer_list:
        signing_time_str = datetime.utcfromtimestamp(
            signer["signingTime"]).strftime("%Y/%m/%d %H:%M:%S UTC")
        signer_list_str = signer_list_str + \
            f"{signer['name']} ({signing_time_str})<br>"
    mail_body = mail_body.replace("DUMMY_SIGNER_LIST", signer_list_str)

    return mail_body


def get_notificant_final_mail_subject(locale, task_id):
    # load email subject
    mail_subject = __load_mail_subject(locale, "email_to_notificant_3")

    # fill task id
    mail_subject = mail_subject.replace("DUMMY_TASK_ID", task_id[-12:])

    return mail_subject


def get_notificant_final_mail_body(locale, file_name, signer_list):
    # load email body
    mail_body = __load_mail_body(locale, "email_to_notificant_3")

    # fill file name
    mail_body = mail_body.replace("DUMMY_FILE_NAME", file_name)

    # fill signers
    signer_list_str = ""
    for signer in signer_list:
        signing_time_str = datetime.utcfromtimestamp(
            signer["signingTime"]).strftime("%Y/%m/%d %H:%M:%S UTC")
        signer_list_str = signer_list_str + \
            f"{signer['name']} ({signing_time_str})<br>"
    mail_body = mail_body.replace("DUMMY_SIGNER_LIST", signer_list_str)

    return mail_body


def get_signer_final_mail_subject(locale, task_id):
    # load email subject
    mail_subject = __load_mail_subject(locale, "email_to_signer_2")

    # fill task id
    mail_subject = mail_subject.replace("DUMMY_TASK_ID", task_id[-12:])

    return mail_subject


def get_signer_final_mail_body(locale):
    # load email body
    mail_body = __load_mail_body(locale, "email_to_signer_2")

    return mail_body
