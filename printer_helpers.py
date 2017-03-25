import os

import barcode
import datetime
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from brother_ql import BrotherQLRaster
from brother_ql import create_label
from brother_ql.backends import backend_factory
from brother_ql.devicedependent import label_type_specs

from barcode_helpers import BrotherLabelWriter


def print_name_label(text, margin=10, rotate=False, label_type="62", printer_type="QL-700",):
    if not rotate:
        width, height = label_type_specs[label_type]['dots_printable']
    else:
        height, width = label_type_specs[label_type]['dots_printable']

    font_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ChopinScript.ttf")
    fs = 2000
    tw, th = width, height
    if width == 0:
        while th + 2*margin > height:
            font = ImageFont.truetype(font_path, fs)
            tw, th = font.getsize(text)
            fs -= 1
        width = tw+2*margin
    elif height == 0:
        while tw + 2*margin > width:
            font = ImageFont.truetype(font_path, fs)
            tw, th = font.getsize(text)
            fs -= 1
        height = th+2*margin
    else:
        while tw + 2*margin > width or th + 2*margin > height:
            font = ImageFont.truetype(font_path, fs)
            tw, th = font.getsize(text)
            fs -= 1

    xp = (width//2)-(tw//2)
    yp = (height//2)-(th//2)

    im = Image.new("RGB", (width, height), (255, 255, 255))
    dr = ImageDraw.Draw(im)

    dr.text((xp, yp), text, fill=(0, 0, 0), font=font)
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d")
    dr.text((0, 0), date, fill=(0, 0, 0))

    base_path = os.path.dirname(os.path.realpath(__file__))
    fn = os.path.join(base_path, "bar_codes", text + ".png")

    im.save(fn, "PNG")
    print_image(fn, printer_type, label_type)


def print_bar_code(barcode_value, barcode_text, barcode_type="ean13", rotate=False, printer_type="QL-700",
                   label_type="62"):
    bar_coder = barcode.get_barcode_class(barcode_type)
    wr = BrotherLabelWriter(typ=label_type, rot=rotate, text=barcode_text, max_height=1000)

    test = bar_coder(barcode_value, writer=wr)
    base_path = os.path.dirname(os.path.realpath(__file__))
    fn = test.save(os.path.join(base_path, "bar_codes", barcode_value))
    print_image(fn, printer_type, label_type)


def print_image(fn, printer_type="QL-700", label_type="62"):
    qlr = BrotherQLRaster(printer_type)
    qlr.exception_on_warning = True
    create_label(qlr, fn, label_type, threshold=70, cut=True)

    be = backend_factory("pyusb")
    list_available_devices = be['list_available_devices']
    BrotherQLBackend = be['backend_class']

    ad = list_available_devices()
    assert ad
    string_descr = ad[0]['string_descr']

    printer = BrotherQLBackend(string_descr)

    printer.write(qlr.data)
