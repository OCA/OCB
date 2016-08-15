# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.web.http import Controller, route, request
from openerp.addons.web.controllers.main import _serialize_exception, content_disposition
from openerp.tools import html_escape

import json
from werkzeug import exceptions, url_decode
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse
from werkzeug.datastructures import Headers
from reportlab.graphics.barcode import createBarcodeDrawing


class ReportController(Controller):

    #------------------------------------------------------
    # Report controllers
    #------------------------------------------------------
    @route([
        '/report/<path:converter>/<reportname>',
        '/report/<path:converter>/<reportname>/<docids>',
    ], type='http', auth='user', website=True)
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report_obj = request.registry['report']
        cr, uid, context = request.cr, request.uid, request.context

        if docids:
            docids = [int(i) for i in docids.split(',')]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            # Ignore 'lang' here, because the context in data is the one from the webclient *but* if
            # the user explicitely wants to change the lang, this mechanism overwrites it.
            data['context'] = json.loads(data['context'])
            if data['context'].get('lang'):
                del data['context']['lang']
            context.update(data['context'])

        if converter == 'html':
            html = report_obj.get_html(cr, uid, docids, reportname, data=data, context=context)
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = report_obj.get_pdf(cr, uid, docids, reportname, data=data, context=context)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            raise exceptions.HTTPException(description='Converter %s not implemented.' % converter)

    #------------------------------------------------------
    # Misc. route utils
    #------------------------------------------------------
    @route(['/report/barcode', '/report/barcode/<type>/<path:value>'],
           type='http', auth="user")
    def report_barcode(self, type, value, barmargin=0, backgroundcolor='FFFFFF',
                       barcolor='000000', textalign=None, textmargin=None,
                       width=600, height=100, scale=2.0, humanreadable=0):
        """Controller able to render barcode images thanks to elaphe.
        Samples:
            <img t-att-src="'/report/barcode/QR/%s' % o.name"/>
            <img t-att-src="'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s' %
                ('QR', o.name, 200, 200)"/>

        :param type: Accepted types: 'auspost', 'azteccode', 'codabar',
        'code11', 'code128', 'code25', 'code39', 'code93', 'datamatrix', 'ean',
        'i2of5', 'japanpost', 'kix', 'maxicode', 'msi', 'onecode', 'pdf417',
        'pharmacode', 'plessey', 'postnet', 'qrcode', 'royalmail', 'rss14',
        'symbol', 'upc'
        :param barmargin: Accepted positive and negative values
        :param backgroundcolor: Accepted hex color codes: from 000000 to FFFFFF
        :param barcolor: Accepted hex color codes: from 000000 to FFFFFF
        :param textalign: Accepted values: left, center or right. Used to specify where to
        horizontally position the text.
        :param textmargin: Accepted positive and negative values
        :param scale: Accepted value: float number to set the image scale
        :param humanreadable: Accepted values: 0 (default) or 1. 1 will insert the readable value
        at the bottom of the output image
        """
        try:
            barcode = request.registry['report'].barcode(
                type, value, barmargin=barmargin, backgroundcolor=backgroundcolor,
                barcolor=barcolor, textalign=textalign, textmargin=textmargin,
                width=width, height=height, scale=scale, humanreadable=humanreadable)
        except (ValueError, AttributeError):
            raise exceptions.HTTPException(description='Cannot convert into barcode.')

        return request.make_response(barcode, headers=[('Content-Type', 'image/png')])

    @route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token):
        """This function is used by 'qwebactionmanager.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = json.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        try:
            if type == 'qweb-pdf':
                reportname = url.split('/report/pdf/')[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter='pdf')
                else:
                    # Particular report:
                    data = url_decode(url.split('?')[1]).items()  # decoding the args represented in JSON
                    response = self.report_routes(reportname, converter='pdf', **dict(data))

                cr, uid = request.cr, request.uid
                report = request.registry['report']._get_report_from_name(cr, uid, reportname)
                filename = "%s.%s" % (report.name, "pdf")
                response.headers.add('Content-Disposition', content_disposition(filename))
                response.set_cookie('fileToken', token)
                return response
            elif type =='controller':
                reqheaders = Headers(request.httprequest.headers)
                response = Client(request.httprequest.app, BaseResponse).get(url, headers=reqheaders, follow_redirects=True)
                response.set_cookie('fileToken', token)
                return response
            else:
                return
        except Exception, e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))

    @route(['/report/check_wkhtmltopdf'], type='json', auth="user")
    def check_wkhtmltopdf(self):
        return request.registry['report']._check_wkhtmltopdf()
