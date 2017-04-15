import os

import datetime
from PIL import ImageFont
from brother_ql.devicedependent import label_type_specs

from printer_helpers import print_bar_code

#label_type = "29x90"
#rotate = True
#barcode_value = "7050122105438"
#barcode_text = "Chips"
#printer_type = "QL-700"


from PIL import Image, ImageMode, ImageDraw


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

print_name_label("chrivi", label_type="29x90", rotate=True)