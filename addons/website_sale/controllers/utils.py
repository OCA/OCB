# -*- coding: utf-8 -*-
import werkzeug

from openerp.http import request
from openerp import SUPERUSER_ID

PPG = 20  # Products Per Page
PPR = 4  # Products Per Row

import logging
logger = logging.getLogger(__file__)


try:
    # try to use https://pypi.python.org/pypi/validate_email
    from validate_email import validate_email
except ImportError:
    msg = '"validate_email" package is missing. \
    Install it to have better email validation.'
    logger.warn(msg)

    import re
    EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

    def validate_email(email, verify=False, check_mx=False):
        """ fallback validation.
        `verify` and `check_mx``are just to mimic
        `validate_email.validate_email` signature.
        """
        return EMAIL_REGEX.match(email)

try:
    # improves `validate_email.validate_email` validation
    # see https://pypi.python.org/pypi/validate_email docs
    import DNS # noqa
    HAS_PyDNS = True
except ImportError:
    msg = '"pyDNS" package is missing. \
    Install it to have better email validation.'
    logger.warn(msg)
    HAS_PyDNS = False

try:
    import phonenumbers
    from phonenumbers.phonenumberutil import NumberParseException

    def validate_phonenumber(value):
        try:
            return bool(phonenumbers.parse(value))
        except NumberParseException:
            return False

except ImportError:
    msg = '"phonenumbers" package is missing. \
    Install it to have better email validation.'
    logger.warn(msg)

    def validate_phonenumber(value):
        if not value.isdigit():
            return False
        return True


class table_compute(object):
    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= PPR:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(PPR):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        for p in products:
            x = min(max(p.website_size_x, 1), PPR)
            y = min(max(p.website_size_y, 1), PPR)
            if index >= PPG:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % PPR, pos / PPR, x, y):
                pos += 1
            # if 21st products (index 20) and the last line is full (PPR products in it), break
            # (pos + 1.0) / PPR is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= PPG and ((pos + 1.0) / PPR) > maxy:
                break

            if x == 1 and y == 1:   # simple heuristic for CPU optimization
                minpos = pos / PPR

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos / PPR) + y2][(pos % PPR) + x2] = False
            self.table[pos / PPR][pos % PPR] = {
                'product': p, 'x': x, 'y': y,
                'class': " ".join(map(lambda x: x.html_class or '',
                                      p.website_style_ids))
            }
            if index <= PPG:
                maxy = max(maxy, y + (pos / PPR))
            index += 1

        # Format table according to HTML needs
        rows = self.table.items()
        rows.sort()
        rows = map(lambda x: x[1], rows)
        for col in range(len(rows)):
            cols = rows[col].items()
            cols.sort()
            x += len(cols)
            rows[col] = [c for c in map(lambda x: x[1], cols)
                         if c is not False]

        return rows

        # TODO keep with input type hidden


class QueryURL(object):
    def __init__(self, path='', **args):
        self.path = path
        self.args = args

    def __call__(self, path=None, **kw):
        if not path:
            path = self.path
        for k, v in self.args.iteritems():
            kw.setdefault(k, v)
        l = []
        for k, v in kw.iteritems():
            if v:
                if isinstance(v, list) or isinstance(v, set):
                    l.append(werkzeug.url_encode([(k, i) for i in v]))
                else:
                    l.append(werkzeug.url_encode([(k, v)]))
        if l:
            path += '?' + '&'.join(l)
        return path


def get_attrib_params():
    attrib_list = request.httprequest.args.getlist('attrib')
    attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
    attrib_set = set([v[1] for v in attrib_values])
    return attrib_list, attrib_values, attrib_set


def get_pricelist():
    cr, uid, context, pool = \
        request.cr, request.uid, request.context, request.registry
    sale_order = context.get('sale_order')
    if sale_order:
        pricelist = sale_order.pricelist_id
    else:
        user = pool['res.users'].browse(cr, SUPERUSER_ID, uid,
                                        context=context)
        partner = user.partner_id
        pricelist = partner.property_product_pricelist
    return pricelist
