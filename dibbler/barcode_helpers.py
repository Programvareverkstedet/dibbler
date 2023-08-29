import os

from PIL import ImageFont
from barcode.writer import ImageWriter, mm2px
from brother_ql.devicedependent import label_type_specs


def px2mm(px, dpi=300):
    return (25.4 * px)/dpi


class BrotherLabelWriter(ImageWriter):
    def __init__(self, typ='62', max_height=350, rot=False, text=None):
        super(BrotherLabelWriter, self).__init__()
        assert typ in label_type_specs
        self.rot = rot
        if self.rot:
            self._h, self._w = label_type_specs[typ]['dots_printable']
            if self._w == 0 or self._w > max_height:
                self._w = min(max_height, self._h / 2)
        else:
            self._w, self._h = label_type_specs[typ]['dots_printable']
            if self._h == 0 or self._h > max_height:
                self._h = min(max_height, self._w / 2)
        self._xo = 0.0
        self._yo = 0.0
        self._title = text

    def _init(self, code):
        self.text = None
        super(BrotherLabelWriter, self)._init(code)

    def calculate_size(self, modules_per_line, number_of_lines, dpi=300):
        x, y = super(BrotherLabelWriter, self).calculate_size(modules_per_line, number_of_lines, dpi)

        self._xo = (px2mm(self._w)-px2mm(x))/2
        self._yo = (px2mm(self._h)-px2mm(y))
        assert self._xo >= 0
        assert self._yo >= 0

        return int(self._w), int(self._h)

    def _paint_module(self, xpos, ypos, width, color):
        super(BrotherLabelWriter, self)._paint_module(xpos+self._xo, ypos+self._yo, width, color)

    def _paint_text(self, xpos, ypos):
        super(BrotherLabelWriter, self)._paint_text(xpos+self._xo, ypos+self._yo)

    def _finish(self):
        if self._title:
            width = self._w+1
            height = 0
            max_h = self._h - mm2px(self._yo, self.dpi)
            fs = int(max_h / 1.2)
            font_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "Stranger back in the Night.ttf")
            font = ImageFont.truetype(font_path, 10)
            while width > self._w or height > max_h:
                font = ImageFont.truetype(font_path, fs)
                width, height = font.getsize(self._title)
                fs -= 1
            pos = (
                (self._w-width)//2,
                0 - (height // 8)
            )
            self._draw.text(pos, self._title, font=font, fill=self.foreground)
        return self._image
