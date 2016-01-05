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

import dateutil

import logging
_logger = logging.getLogger(__name__)


class pos_order(osv.osv):
    _name = "pos.order"
    _inherit = "pos.order"


    def action_invoice(self, cr, uid, ids, context=None):
        inv_ref = self.pool.get('account.invoice')
        inv_line_ref = self.pool.get('account.invoice.line')
        product_obj = self.pool.get('product.product')
        res_partner = self.pool.get('res.partner')
        account_voucher_obj = self.pool.get('account.voucher')

        inv_ids = []

        for order in self.pool.get('pos.order').browse(cr, uid, ids, context=context):
            if order.invoice_id:
                inv_ids.append(order.invoice_id.id)
                continue

            if not order.partner_id:
                order.partner_id=res_partner.browse(cr, uid, 1, context=context)
                #raise osv.except_osv(_('Error!'), _('Please provide a partner for the sale.'))

            acc = order.partner_id.property_account_receivable.id
            inv = {
                'name': order.name,
                'origin': order.name,
                'account_id': acc,
                'journal_id': order.sale_journal.id or None,
                'type': 'out_invoice',
                'reference': order.name,
                'partner_id': order.partner_id.id,
                'comment': order.note or '',
                'currency_id': order.pricelist_id.currency_id.id, # considering partner's sale pricelist's currency
            }
            inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', order.partner_id.id)['value'])
            if not inv.get('account_id', None):
                inv['account_id'] = acc
            inv_id = inv_ref.create(cr, uid, inv, context=context)

            self.write(cr, uid, [order.id], {'invoice_id': inv_id, 'state': 'invoiced'}, context=context)
            inv_ids.append(inv_id)
            for line in order.lines:
                inv_line = {
                    'invoice_id': inv_id,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                }
                inv_name = product_obj.name_get(cr, uid, [line.product_id.id], context=context)[0][1]
                inv_line.update(inv_line_ref.product_id_change(cr, uid, [],
                                                               line.product_id.id,
                                                               line.product_id.uom_id.id,
                                                               line.qty, partner_id = order.partner_id.id,
                                                               fposition_id=order.partner_id.property_account_position.id)['value'])
                if not inv_line.get('account_analytic_id', False):
                    inv_line['account_analytic_id'] = \
                        self._prepare_analytic_account(cr, uid, line,
                                                       context=context)
                inv_line['price_unit'] = line.price_unit
                inv_line['discount'] = line.discount
                inv_line['name'] = inv_name
                inv_line['invoice_line_tax_id'] = [(6, 0, inv_line['invoice_line_tax_id'])]
                inv_line_ref.create(cr, uid, inv_line, context=context)
            inv_ref.button_reset_taxes(cr, uid, [inv_id], context=context)
            self.signal_workflow(cr, uid, [order.id], 'invoice')
            inv_ref.signal_workflow(cr, uid, [inv_id], 'validate')
            inv_ref.invoice_open(cr, uid, [inv_id], context=context)
            '''
            for statement in order.statement_ids:                 
                _logger.info('statement %r', statement)
                voucher_data = {
                    'partner_id': order.partner_id['id'],
                    'amount': abs(statement['amount']),
                    'journal_id': statement['journal_id']['id'],
                    'period_id': account_voucher_obj._get_period(cr, uid),
                    'account_id': order.partner_id['property_account_receivable']['id'],
                    'type': 'receipt' ,
                    'reference' : order.name,
                }
                voucher_id = account_voucher_obj.create(cr, uid, voucher_data, context=context)
                account_voucher_obj.signal_workflow(cr, uid, [voucher_id], 'proforma_voucher')
            '''


        if not inv_ids: return {}

        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False

        return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }

    def _fnct_endocenas(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            total=0.0
            for lines in order.lines :
                if lines.product_id.uom_id.category_id.name == 'Unidad': 
                    logging.info('producto %s',lines.product_id.uom_id.category_id.name)

                    amount = lines.qty/lines.product_id.uom_id.factor

                    total  = total + amount * lines.product_id.uos_id.factor
            res[order.id] = total
        return res

    def _fnct_enkilos(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            total=0.0

            for lines in order.lines :
                if lines.product_id.uom_id.category_id.name == 'Peso': 
                    logging.info('producto %s',lines.product_id.uom_id.category_id.name)

                    amount = lines.qty/lines.product_id.uom_id.factor
                    total  = total + amount * lines.product_id.uos_id.factor
            res[order.id] = total
        return res

    def _fnct_price_huevos(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            total=0.0

            for lines in order.lines :
                if lines.product_id.uom_id.category_id.name == 'Unidad': 
                    total  = total + lines.price_subtotal
            res[order.id] = total
        return res

    def _fnct_price_alimento(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            total=0.0

            for lines in order.lines :
                if lines.product_id.uom_id.category_id.name == 'Peso': 
                    total  = total + lines.price_subtotal
            res[order.id] = total
        return res


    _columns = {
        'statement_ids': fields.one2many('account.bank.statement.line', 'pos_statement_id', 'Payments',  readonly=False),
        'total_endocenas': fields.function(_fnct_endocenas, string='Doc',type='float',),
        'total_enkilos': fields.function(_fnct_enkilos, string='Kg',type='float',),

        'price_huevos': fields.function(_fnct_price_huevos, string='$ H',type='float',),
        'price_alimento': fields.function(_fnct_price_alimento, string='$ A',type='float',),


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


