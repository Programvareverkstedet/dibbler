import re

from dibbler.conf import config
from dibbler.models import Product, User
from dibbler.printer_helpers import print_bar_code, print_name_label

from .helpermenus import Menu


class PrintLabelMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Print a label', uses_db=True)
        self.help_text = '''
Prints out a product bar code on the printer

Put it up somewhere in the vicinity.
'''

    def _execute(self):
        self.print_header()

        thing = self.input_thing('Product/User')

        if isinstance(thing, Product):
            if re.match(r"^[0-9]{13}$", thing.bar_code):
                bar_type = "ean13"
            elif re.match(r"^[0-9]{8}$", thing.bar_code):
                bar_type = "ean8"
            else:
                bar_type = "code39"
            print_bar_code(
                thing.bar_code,
                thing.name,
                barcode_type=bar_type,
                rotate=config.getboolean('printer', 'rotate'),
                printer_type="QL-700",
                label_type=config.get('printer', 'label_type'),
            )
        elif isinstance(thing, User):
            print_name_label(
                text=thing.name,
                label_type=config.get('printer', 'label_type'),
                rotate=config.getboolean('printer', 'rotate'),
                printer_type="QL-700"
            )
