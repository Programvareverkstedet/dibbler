from db import Product, User
from printer_helpers import print_bar_code, print_name_label
from text_interface.helpermenus import Menu
import conf


class PrintLabelMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Print a label', uses_db=True)
        self.help_text = '''
Prints out a product bar code on the printer

Put it up somewhere in the vicinity.
'''

    def _execute(self):
        self.print_header()

        thing = self.input_thing('Prodct/User> ')

        if isinstance(thing, Product):
            if len(thing.bar_code) == 13:
                bar_type = "ean13"
            elif len(thing.bar_code) == 8:
                bar_type = "ean8"
            else:
                bar_type = "code39"
            print_bar_code(thing.bar_code, thing.name, barcode_type=bar_type, rotate=conf.label_rotate,
                           printer_type="QL-700", label_type=conf.label_type)
        elif isinstance(thing, User):
            print_name_label(text=thing.name, label_type=conf.label_type, rotate=conf.label_rotate,
                             printer_type="QL-700")
