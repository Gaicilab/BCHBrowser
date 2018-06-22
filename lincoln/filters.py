from math import log10, floor
from decimal import Decimal

import bitcoin.core as core
import datetime
import ago


def sig_round(x, sig=2):
    try:
        if x == 0:
            return "0"
        whole = int(str(x).split(".")[0])
        if whole != x:
            x -= whole
        else:
            whole = 0
        return "{:,f}".format(whole + round(x, sig - int(floor(log10(abs(x)))) - 1)).rstrip('0').rstrip('.')
    except Exception:
        return "Err. Will fix soon"


def duration(seconds):
    # microseconds
    if seconds > 3600:
        return "{}".format(datetime.timedelta(seconds=seconds))
    if seconds > 60:
        return "{:,.2f} mins".format(seconds / 60.0)
    if seconds <= 1.0e-3:
        return "{:,.4f} us".format(seconds * 1000000.0)
    if seconds <= 1.0:
        return "{:,.4f} ms".format(seconds * 1000.0)
    return "{:,.4f} sec".format(seconds)


def humana_date(*args, **kwargs):
    return ago.human(*args, **kwargs)


def hashrate(hashrate, num_fmt="{:,.2f}", sec=True):
    unit = "/s" if sec else ""
    if hashrate > 1000000000:
        return "{} GH{}".format(num_fmt.format(hashrate / 1000000000), unit)
    if hashrate > 1000000:
        return "{} MH{}".format(num_fmt.format(hashrate / 1000000), unit)
    if hashrate > 1000:
        return "{} KH{}".format(num_fmt.format(hashrate / 1000), unit)
    return "{} H{}".format(num_fmt.format(hashrate), unit)


def human_date_utc(*args, **kwargs):
    if isinstance(args[0], (int, float, str)):
        args = [datetime.datetime.utcfromtimestamp(float(args[0]))] + list(args[1:])
    delta = (datetime.datetime.utcnow() - args[0])
    delta = delta - datetime.timedelta(microseconds=delta.microseconds)
    return ago.human(delta, *args[1:], **kwargs)


def comma(value):
    if isinstance(value, (float, Decimal)):
        return "{:,.2f}".format(value)
    elif isinstance(value, int):
        return "{:,}".format(value)
    else:
        return "NaN"


def currency(value):
    return "{:,.8f}".format(float(value))


def bytes(val):
    return core.b2lx(val)
