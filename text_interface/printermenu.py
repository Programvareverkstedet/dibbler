from printer_helpers import print_bar_code
from text_interface.helpermenus import Menu
import conf


class PrintLabelMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Print bar code', uses_db=True)
        self.help_text = '''
Prints out a product bar code on the printer

Put it up somewhere in the vicinity.
'''

    def _execute(self):
        self.print_header()
        product = self.input_product('Prodct> ')

        print_bar_code(product.bar_code, product.name, barcode_type="ean13", rotate=conf.label_rotate,
                       printer_type="QL-700", label_type=conf.label_type)
