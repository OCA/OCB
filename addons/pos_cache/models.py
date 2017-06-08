# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import datetime
import cPickle

from openerp import models, fields, api

class pos_cache(models.Model):
    _name = 'pos.cache'

    cache = fields.Binary()
    cachetime = fields.Datetime()
    config_ids = fields.One2many('pos.config', 'cache_id', 'Config')

    @api.model
    def refresh_all_caches(self):
        caches = self.search([('config_ids', '=', False)])
        if caches:
            caches.unlink()
        self.env['pos.config'].search([('state', '=', 'active')]).recomputeCache()
            
    @api.one
    def refresh_cache(self):
        products = self.env['product.product'].search(self._get_domain())
        prod_ctx = products.with_context(pricelist=self.config_ids[0].pricelist_id.id, display_default_code=False)
        if self.config_ids[0].cachecomputeuser_id:
            prod_ctx = prod_ctx.sudo(self.config_ids[0].cachecomputeuser_id.id)
        res = prod_ctx.read(self._get_fields())
        writed=False
        retries=0
        datas = {
            'cache': cPickle.dumps(res, protocol=cPickle.HIGHEST_PROTOCOL),
            'cachetime': fields.Datetime.now(),
        }
        while not writed and retries<=5:
            try:
                self.write(datas)
                writed=True
            except Exception, e:
                retries+=1
                if retries>5:
                    raise Exception(e)
        
    def _get_domain(self):
        return [('sale_ok', '=', True), ('available_in_pos', '=', True)]

    def _get_fields(self):
        return ['display_name', 'list_price','price','pos_categ_id', 'taxes_id', 'ean13', 'default_code', 
                 'to_weight', 'uom_id', 'uos_id', 'uos_coeff', 'mes_type', 'description_sale', 'description',
                 'product_tmpl_id']


class pos_config(models.Model):
    _inherit = 'pos.config'

    #Use a related model to avoid the load of the cache when the pos load his config
    cache_id = fields.Many2one('pos.cache', 'Cache')
    cachecomputeuser_id = fields.Many2one('res.users', 'Cache compute user', help="User used to compute the cache content and thus avoid the bad practice of using admin in multi-company")
    cachetime = fields.Datetime(related='cache_id.cachetime', string='Last cache compute')
    
    @api.multi
    def getProductsFromCache(self):
        if not self.cache_id or not self.cache_id.cachetime:
            self.recomputeCache()
        return cPickle.loads(self.cache_id.cache)

    @api.one
    def recomputeCache(self):
        if not self.cache_id:
            self.cache_id = self.cache_id.create({})
        self.cache_id.refresh_cache()
        
