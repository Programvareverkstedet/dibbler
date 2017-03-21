from PIL import ImageFont
from barcode.writer import ImageWriter, mm2px
from brother_ql.devicedependent import label_type_specs


def px2mm(px, dpi=300):
    return (25.4 * px)/dpi


class BrotherLabelWriter(ImageWriter):
    def __init__(self, typ='62', max_height=350, rot=0, text=None):
        super().__init__()
        assert typ in label_type_specs
        if (rot//90) % 2 == 1:
            self._h, self._w = label_type_specs[typ]['dots_printable']
            if self._w == 0 or self._w > max_height:
                self._w = max_height
        if (rot//90) % 2 == 0:
            self._w, self._h = label_type_specs[typ]['dots_printable']
            if self._h == 0 or self._h > max_height:
                self._h = max_height
        self._xo = 0.0
        self._yo = 0.0
        self._title = text

    def _init(self, code):
        self.text = None
        super()._init(code)

    def calculate_size(self, modules_per_line, number_of_lines, dpi=300):
        x, y = super().calculate_size(modules_per_line, number_of_lines, dpi)

        self._xo = (px2mm(self._w)-px2mm(x))/2
        self._yo = (px2mm(self._h)-px2mm(y))
        assert self._xo >= 0
        assert self._yo >= 0

        return int(self._w), int(self._h)

    def _paint_module(self, xpos, ypos, width, color):
        super()._paint_module(xpos+self._xo, ypos+self._yo, width, color)

    def _paint_text(self, xpos, ypos):
        super()._paint_text(xpos+self._xo, ypos+self._yo)

    def _finish(self):
        if self._title:
            width = self._w+1
            height = 0
            max_h = self._h - mm2px(self._yo, self.dpi)
            fs = int(max_h / 1.2)
            font = ImageFont.truetype("arial.ttf", 10)
            while width > self._w or height > max_h:
                font = ImageFont.truetype("Stranger back in the Night.ttf", fs)
                width, height = font.getsize(self._title)
                fs -= 1
            pos = (
                (self._w-width)//2,
                mm2px(0, self.dpi)
            )
            self._draw.text(pos, self._title, font=font, fill=self.foreground)
        return self._image
