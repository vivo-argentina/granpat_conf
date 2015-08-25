# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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

import openerp
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round, float_compare

import logging
_logger = logging.getLogger(__name__)


class pos_order(osv.osv):
    _name = "pos.order"
    _inherit = "pos.order"
    _columns = {
        'statement_ids': fields.one2many('account.bank.statement.line', 'pos_statement_id', 'Payments',  readonly=False),

        }

    _defaults = {
        }


class pos_order_line(osv.osv):
    _name = "pos.order.line"
    _inherit = "pos.order.line"
    _columns = {

        }

    _defaults = {
        }

    def show_special_quantity(self,product_id,qty):
        logging.info('producto %s',product_id.uom_id.category_id.name)
        amount = qty/product_id.uom_id.factor


        amount = amount * product_id.uos_id.factor
        return  str(float_round(amount, precision_rounding=product_id.uos_id.rounding)) + ' ' + product_id.uos_id.name 


