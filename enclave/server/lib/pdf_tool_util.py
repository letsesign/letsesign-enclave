import io
import base64
import logging
import traceback

from pikepdf import Pdf, Page, Encryption
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from lib.pdf_font_util import DANCING_SCRIPT_UNICODE_TABLE

LINE_WIDTH = 6
HINT_MSG_X_OFFSET = 6
HINT_HEIGHT_RATIO = 0.25
SIG_MSG_X_OFFSET = 3
SIG_HEIGHT_RATIO = 0.6
TEXT_HEIGHT_RATIO = 1
HANAMIN_FONT_FACTOR = 1.2

FIELD_TYPE_SIGNATURE = 0
FIELD_TYPE_DATE = 1

SEAL_IMAGE_FILE_PATH = "/server/resources/img/seal.png"
HANAMIN_FONT_FILE_PATH = "/server/resources/font/HanaMinA.ttf"
INCONSOLATA_FONT_FILE_PATH = "/server/resources/font/Inconsolata-Regular.ttf"
DANCING_SCRIPT_FONT_FILE_PATH = "/server/resources/font/DancingScript-Regular.ttf"
JASON_HANDWRITING_FONT_FILE_PATH = "/server/resources/font/JasonHandwriting2-Regular.ttf"


def __check_unicode_exist(font_unicode_table, code):
    for range_item in font_unicode_table:
        if int(range_item["begin"], 16) <= code and code <= int(range_item["end"], 16):
            return True

    return False


def __get_sign_hint_msg(locale):
    lowercase_locale = locale.lower()

    if lowercase_locale == "zh-tw":
        return ["您的簽名將顯示在這裡"]
    else:
        return ["Your signature will", "be placed here"]


def __check_pdf_boundary(page_width, page_height, x_pos, y_pos, height):
    if x_pos < 0 or x_pos > page_width:
        raise Exception("x position of filed is out of range")

    if y_pos < 0 or y_pos > page_height:
        raise Exception("y position of filed is out of range")

    if (y_pos + height) > page_height:
        raise Exception("height of filed is out of range")


def __draw_border_(canvas_obj, page_height, x_pos, y_pos, height):
    canvas_obj.setLineWidth(LINE_WIDTH)
    canvas_obj.setStrokeColorRGB(0.203, 0.596, 0.858)
    canvas_obj.line(x_pos + LINE_WIDTH / 2, page_height - (y_pos + height),
                    x_pos + LINE_WIDTH / 2, page_height - y_pos)


def __draw_seal_image(canvas_obj, page_height, x_pos, y_pos, height):
    canvas_obj.drawImage(SEAL_IMAGE_FILE_PATH, x_pos,
                         page_height - (y_pos + height), height, height, "auto")


def __draw_sign_hint(canvas_obj, page_height, x_pos, y_pos, height, locale):
    # draw border
    __draw_border_(canvas_obj, page_height, x_pos, y_pos, height)

    sign_hint_msg = __get_sign_hint_msg(locale)
    hint_font_size = 1
    remaining_height = 0

    # find best fit font size
    while True:
        render_height = pdfmetrics.getAscent(
            "HanaMinA", hint_font_size) * HANAMIN_FONT_FACTOR * len(sign_hint_msg)

        if render_height / height <= HINT_HEIGHT_RATIO * len(sign_hint_msg):
            hint_font_size += 0.1
        else:
            hint_font_size -= 0.1
            remaining_height = height - \
                pdfmetrics.getAscent(
                    "HanaMinA", hint_font_size) * HANAMIN_FONT_FACTOR * len(sign_hint_msg)
            break

    # # draw hint message
    canvas_obj.setFillColorRGB(0.203, 0.596, 0.858)
    canvas_obj.setFont("HanaMinA", hint_font_size)
    for index, msg in enumerate(sign_hint_msg):
        canvas_obj.drawString(x_pos + LINE_WIDTH / 2 + HINT_MSG_X_OFFSET, page_height - (y_pos + remaining_height /
                              2 + pdfmetrics.getAscent("HanaMinA", hint_font_size) * HANAMIN_FONT_FACTOR * (index + 1)), msg)


def __draw_sig_field(is_preview, canvas_obj, page_height, x_pos, y_pos, height, name, magic_number, signer_idx):
    # draw seal image
    __draw_seal_image(canvas_obj, page_height, x_pos, y_pos, height)

    x_offset = height
    signature_font = "DancingScript-Regular"
    signature_font_size = 1
    info_font_size = height / 5

    # choose font for signature
    for char in name:
        if not __check_unicode_exist(DANCING_SCRIPT_UNICODE_TABLE, ord(char)):
            signature_font = "JasonHandwriting2-Regular"
            break

    # find best fit font size
    while True:
        render_height = pdfmetrics.getAscent(
            signature_font, signature_font_size)

        if render_height / height <= SIG_HEIGHT_RATIO:
            signature_font_size += 0.1
        else:
            signature_font_size -= 0.1
            break

    # draw signature name
    canvas_obj.setFillColorRGB(0.015, 0.109, 0.674)
    canvas_obj.setFont(signature_font, signature_font_size)
    canvas_obj.drawString(x_pos + x_offset + SIG_MSG_X_OFFSET, page_height - (
        y_pos + pdfmetrics.getAscent(signature_font, signature_font_size)), name)

    # draw signature magic number
    if not is_preview:
        canvas_obj.setFillColorRGB(0, 0, 0)
        canvas_obj.setFont("Inconsolata-Regular", info_font_size)
        signer_idx_str = f"00{signer_idx}"[-2:]
        canvas_obj.drawString(x_pos + x_offset + SIG_MSG_X_OFFSET, page_height - (y_pos + height -
                              pdfmetrics.getAscent("Inconsolata-Regular", info_font_size) / 5), f"{magic_number} ({signer_idx_str})")


def __draw_text_field(canvas_obj, page_height, x_pos, y_pos, height, text):
    text_font_size = height

    # draw text
    canvas_obj.setFillColorRGB(0, 0, 0)
    canvas_obj.setFont("Inconsolata-Regular", text_font_size)
    canvas_obj.drawString(x_pos, page_height - (y_pos + height), text)


def __preview_page_render_fn(page_obj, field_list_in_page):
    page_width = float(page_obj.MediaBox[2] - page_obj.MediaBox[0])
    page_height = float(page_obj.MediaBox[3] - page_obj.MediaBox[1])

    needOverlay = False
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    for field in field_list_in_page:
        __check_pdf_boundary(page_width, page_height,
                             field["x"], field["y"], field["height"])

        if field["type"] == FIELD_TYPE_SIGNATURE:
            if field["signHint"]:
                needOverlay = True
                __draw_sign_hint(
                    can, page_height, field["x"], field["y"], field["height"], field["locale"])
            else:
                needOverlay = True
                __draw_sig_field(
                    True, can, page_height, field["x"], field["y"], field["height"], field["name"], "", field["idx"])

    can.save()
    packet.seek(0)

    if needOverlay:
        new_pdf = Pdf.open(packet)
        page_obj.add_overlay(Page(new_pdf.pages[0]))


def __signed_page_render_fn(page_obj, field_list_in_page):
    page_width = float(page_obj.MediaBox[2] - page_obj.MediaBox[0])
    page_height = float(page_obj.MediaBox[3] - page_obj.MediaBox[1])

    needOverlay = False
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    for field in field_list_in_page:
        __check_pdf_boundary(page_width, page_height,
                             field["x"], field["y"], field["height"])

        if field["type"] == FIELD_TYPE_SIGNATURE:
            needOverlay = True
            __draw_sig_field(
                False, can, page_height, field["x"], field["y"], field["height"], field["name"], field["magicNumber"], field["idx"])
        elif field["type"] == FIELD_TYPE_DATE:
            needOverlay = True
            __draw_text_field(
                can, page_height, field["x"], field["y"], field["height"], field["signingTime"])

    can.save()
    packet.seek(0)

    if needOverlay:
        new_pdf = Pdf.open(packet)
        page_obj.add_overlay(Page(new_pdf.pages[0]))


def __pdf_drawing_helper(pdf_bytes, field_list_by_page, render_fn):
    input_pdf = Pdf.open(io.BytesIO(pdf_bytes))
    output_pdf_stream = io.BytesIO()

    for page_no in field_list_by_page:
        if page_no < 1 or page_no > len(input_pdf.pages):
            raise Exception("pageNo of filed is out of range")

        render_fn(input_pdf.pages[page_no - 1], field_list_by_page[page_no])

    input_pdf.save(output_pdf_stream, min_version="1.7")
    return output_pdf_stream.getvalue()


def __pdf_encryption_helper(pdf_bytes, access_key):
    input_pdf = Pdf.open(io.BytesIO(pdf_bytes))
    output_pdf_stream = io.BytesIO()

    input_pdf.save(output_pdf_stream, min_version="1.7",
                   encryption=Encryption(owner=access_key, user=access_key))
    return output_pdf_stream.getvalue()


def __pdf_metadata_helper(pdf_bytes):
    metadata = "letsesign=true\n"

    if pdf_bytes[-1] != 10:
        metadata = f"\n{metadata}"

    return b"".join([pdf_bytes, metadata.encode("utf-8")])


def init():
    pdfmetrics.registerFont(TTFont("HanaMinA", HANAMIN_FONT_FILE_PATH))
    pdfmetrics.registerFont(
        TTFont("Inconsolata-Regular", INCONSOLATA_FONT_FILE_PATH))
    pdfmetrics.registerFont(
        TTFont("DancingScript-Regular", DANCING_SCRIPT_FONT_FILE_PATH))
    pdfmetrics.registerFont(
        TTFont("JasonHandwriting2-Regular", JASON_HANDWRITING_FONT_FILE_PATH))


def gen_preview_pdf(pdf_b64, signer_list, password):
    out_pdf_b64 = None

    try:
        field_list_by_page = {}

        # sort field by page
        for signerIdx, signer in enumerate(signer_list):
            for field in signer["fieldList"]:
                if field["pageNo"] not in field_list_by_page:
                    field_list_by_page[field["pageNo"]] = []

                field_list_by_page[field["pageNo"]].append({
                    "idx": signerIdx + 1,
                    "locale": signer["locale"],
                    "signHint": signer["signHint"],
                    "name": signer["name"],
                    "emailAddr": signer["emailAddr"],
                    "phoneNumber": signer.get("phoneNumber"),
                    "x": field["x"],
                    "y": field["y"],
                    "height": field["height"],
                    "pageNo": field["pageNo"],
                    "type": field["type"]
                })

        output_drew_pdf_bytes = __pdf_drawing_helper(base64.b64decode(
            pdf_b64), field_list_by_page, __preview_page_render_fn)

        # encrypt pdf if needed
        if password:
            output_encrypted_pdf_bytes = __pdf_encryption_helper(
                output_drew_pdf_bytes, password)
            out_pdf_b64 = base64.b64encode(
                output_encrypted_pdf_bytes).decode("utf-8")
        else:
            out_pdf_b64 = base64.b64encode(
                output_drew_pdf_bytes).decode("utf-8")
    except BaseException as e:
        logging.error(traceback.format_exc())

    return out_pdf_b64


def gen_signed_pdf(pdf_b64, signer_list, magic_number):
    out_pdf_b64 = None

    try:
        field_list_by_page = {}
        short_magic_number = magic_number[:32] if len(
            magic_number) > 32 else magic_number

        # sort field by page
        for signerIdx, signer in enumerate(signer_list):
            for field in signer["fieldList"]:
                if field["pageNo"] not in field_list_by_page:
                    field_list_by_page[field["pageNo"]] = []

                field_list_by_page[field["pageNo"]].append({
                    "idx": signerIdx + 1,
                    "locale": signer["locale"],
                    "name": signer["name"],
                    "emailAddr": signer["emailAddr"],
                    "signingTime": signer["signingTime"],
                    "phoneNumber": signer.get("phoneNumber"),
                    "magicNumber": short_magic_number,
                    "x": field["x"],
                    "y": field["y"],
                    "height": field["height"],
                    "pageNo": field["pageNo"],
                    "type": field["type"]
                })

        output_drew_pdf_bytes = __pdf_drawing_helper(base64.b64decode(
            pdf_b64), field_list_by_page, __signed_page_render_fn)
        output_metadata_pdf_bytes = __pdf_metadata_helper(
            output_drew_pdf_bytes)
        out_pdf_b64 = base64.b64encode(
            output_metadata_pdf_bytes).decode("utf-8")
    except BaseException as e:
        logging.error(traceback.format_exc())

    return out_pdf_b64
