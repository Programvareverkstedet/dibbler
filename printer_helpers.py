import barcode
from brother_ql import BrotherQLRaster
from brother_ql import create_label
from brother_ql.backends import backend_factory

from barcode_helpers import BrotherLabelWriter


def print_bar_code(barcode_value, barcode_text, barcode_type="ean13", rotate=False, printer_type="QL-700",
                   label_type="62"):
    bar_coder = barcode.get_barcode_class(barcode_type)
    wr = BrotherLabelWriter(typ=label_type, rot=rotate, text=barcode_text, max_height=1000)

    test = bar_coder(barcode_value, writer=wr)
    fn = test.save(barcode_value)
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