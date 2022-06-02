import ssl
import base64
import logging
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import python_http_client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, TrackingSettings, ClickTracking, OpenTracking, SubscriptionTracking, Ganalytics, Attachment, FileContent, FileName, FileType, Disposition

from lib import mail_template
from lib.err_code_util import ErrCodeList

EMAIL_DISPLAY_NAME = "Let's eSign"
SES_SMTP_HOST = "email-smtp.us-east-1.amazonaws.com"
SES_SMTP_PORT = 587


class MailSender():
    def __init__(self, email_config):
        self.email_config = email_config

    def __send_mail_via_ses(self, to_email, subject, mail_body, attachment_info=None):
        from_mail = f"=?UTF-8?B?{base64.b64encode(EMAIL_DISPLAY_NAME.encode('utf-8')).decode('utf-8')}?= <do-not-reply@{self.email_config['sesDomain']}>"

        # set headers
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = from_mail
        message["To"] = to_email

        # set HTML body
        part = MIMEText(mail_body, "html", "utf-8")
        message.attach(part)

        # set PDF attachment
        if attachment_info:
            part = MIMEApplication(attachment_info["fileBytes"])
            part.add_header("Content-Disposition", "attachment",
                            filename=attachment_info["fileName"])
            part.add_header("Content-Type", attachment_info["contentType"])
            message.attach(part)

        with smtplib.SMTP(SES_SMTP_HOST, port=SES_SMTP_PORT, timeout=10) as smtp_server:
            smtp_server.ehlo()
            smtp_server.starttls(context=ssl.create_default_context())
            smtp_server.login(
                self.email_config["sesSMTPUsername"], self.email_config["sesSMTPPassword"])
            smtp_server.sendmail(from_mail, to_email, message.as_string())
            smtp_server.quit()

    def __send_mail_via_sendgrid(self, to_email, subject, mail_body, attachment_info=None):
        response = None

        try:
            from_mail = f"do-not-reply@{self.email_config['sgDomain']}"

            message = Mail(from_email=(from_mail, EMAIL_DISPLAY_NAME),
                           to_emails=to_email, subject=subject, html_content=mail_body)
            message.tracking_settings = TrackingSettings(ClickTracking(
                False, False), OpenTracking(False), SubscriptionTracking(False), Ganalytics(False))

            if attachment_info:
                attachment = Attachment()
                attachment.file_content = FileContent(
                    base64.b64encode(attachment_info["fileBytes"]).decode())
                attachment.file_type = FileType(attachment_info["contentType"])
                attachment.file_name = FileName(
                    f"=?UTF-8?B?{base64.b64encode(attachment_info['fileName'].encode('utf-8')).decode('utf-8')}?=")
                attachment.disposition = Disposition("attachment")
                message.attachment = attachment

            sg_client = SendGridAPIClient(self.email_config["sgSecret"])
            response = sg_client.send(message)

            if response.status_code != 202 and response.status_code != 200:
                raise RuntimeError(
                    f"failed to send email via sendgrid: {response.status_code}")
        except python_http_client.exceptions.UnauthorizedError as e:
            raise e
        except BaseException as e:
            raise RuntimeError(str(e))

    def __send_mail(self, to_email, subject, mail_body, attachment_info=None):
        try:
            if self.email_config["serviceProvider"] == "ses":
                self.__send_mail_via_ses(
                    to_email, subject, mail_body, attachment_info)
            elif self.email_config["serviceProvider"] == "sg":
                self.__send_mail_via_sendgrid(
                    to_email, subject, mail_body, attachment_info)
            else:
                raise RuntimeError(f"unsupported email service provider")

            return ErrCodeList.SUCCES.value
        except smtplib.SMTPAuthenticationError as e:
            return ErrCodeList.INVALID_EMAIL_CREDENTIAL.value
        except python_http_client.exceptions.UnauthorizedError as e:
            return ErrCodeList.INVALID_EMAIL_CREDENTIAL.value
        except BaseException as e:
            logging.error(traceback.format_exc())
            return ErrCodeList.SEND_EMAIL_FAIL.value

    def send_notificant_error_mail(self, locale, notificant_email, task_id, file_name, single_signer_email):
        try:
            subject = mail_template.get_error_mail_subject(locale, task_id)
            mail_body = mail_template.get_error_mail_body(
                locale, file_name, single_signer_email)

            return self.__send_mail(notificant_email, subject, mail_body)
        except BaseException as e:
            logging.error(traceback.format_exc())
            return ErrCodeList.SEND_EMAIL_FAIL.value

    def send_notificant_notify_mail(self, locale, notificant_email, task_id, file_name, single_signer_email):
        try:
            subject = mail_template.get_notify_mail_subject(locale, task_id)
            mail_body = mail_template.get_notify_mail_body(
                locale, file_name, single_signer_email)

            return self.__send_mail(notificant_email, subject, mail_body)
        except BaseException as e:
            logging.error(traceback.format_exc())
            return ErrCodeList.SEND_EMAIL_FAIL.value

    def send_signer_confirmation_mail(self, locale, sig_sender, sig_signer_addr, task_id, signer_name, custom_message, file_name, pdf_b64, confirm_link, signer_phone):
        try:
            pdf_bytes = base64.b64decode(pdf_b64)
            subject = mail_template.get_confirm_mail_subject(locale, task_id)
            mail_body = mail_template.get_confirm_mail_body(
                locale, sig_sender, signer_name, custom_message, confirm_link, signer_phone)
            attachment_info = {
                "fileBytes": pdf_bytes,
                "fileName": file_name,
                "contentType": "application/pdf"
            }

            return self.__send_mail(sig_signer_addr, subject, mail_body, attachment_info)
        except BaseException as e:
            logging.error(traceback.format_exc())
            return ErrCodeList.SEND_EMAIL_FAIL.value

    def send_notificant_signed_event_mail(self, locale, notificant_email, task_id, file_name, signer_list):
        try:
            subject = mail_template.get_signed_event_mail_subject(
                locale, task_id)
            mail_body = mail_template.get_signed_event_mail_body(
                locale, file_name, signer_list)

            return self.__send_mail(notificant_email, subject, mail_body)
        except BaseException as e:
            logging.error(traceback.format_exc())
            return ErrCodeList.SEND_EMAIL_FAIL.value

    def send_notificant_final_mail(self, locale, notificant_email, task_id, file_name, signer_list, zip_file_name, zip_file_bytes):
        try:
            subject = mail_template.get_notificant_final_mail_subject(
                locale, task_id)
            mail_body = mail_template.get_notificant_final_mail_body(
                locale, file_name, signer_list)
            attachment_info = {
                "fileBytes": zip_file_bytes,
                "fileName": zip_file_name,
                "contentType": "application/zip"
            }

            return self.__send_mail(notificant_email, subject, mail_body, attachment_info)
        except BaseException as e:
            logging.error(traceback.format_exc())
            return ErrCodeList.SEND_EMAIL_FAIL.value

    def send_signer_final_mail(self, locale, signer_email, task_id, zip_file_name, zip_file_bytes):
        try:
            subject = mail_template.get_signer_final_mail_subject(
                locale, task_id)
            mail_body = mail_template.get_signer_final_mail_body(locale)
            attachment_info = {
                "fileBytes": zip_file_bytes,
                "fileName": zip_file_name,
                "contentType": "application/zip"
            }

            return self.__send_mail(signer_email, subject, mail_body, attachment_info)
        except BaseException as e:
            logging.error(traceback.format_exc())
            return ErrCodeList.SEND_EMAIL_FAIL.value
