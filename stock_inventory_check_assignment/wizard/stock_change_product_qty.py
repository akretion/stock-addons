# -*- coding: utf-8 -*-
###############################################################################
#
#    Module for OpenERP
#    Copyright (C) 2015 Akretion (http://www.akretion.com). All Rights Reserved
#    @author Florian DA COSTA <florian.dacosta@akretion.com>
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
###############################################################################

from openerp.osv import orm, fields
from tools.translate import _
import netsvc

class StockChangeProductQty(orm.TransientModel):
    _inherit = "stock.change.product.qty"

    _columns = {
        'qty_to_unserserve': fields.float('Qty to Un-reserve'),
        'move_line_ids': fields.one2many(
            'move.line.wizard', 'inventory_wizard_id', 'Move List'),
    }

    def onchange_new_qty(self, cr, uid, ids, new_quantity=None, product_id=None, context=None):
        if context is None:
            context = {}
        result = {}
        moves_vals = []
        if product_id:
            prod_obj = self.pool['product.product']
            product = self.pool['product.product'].browse(cr, uid, product_id, context=context)
            qty_available = product.qty_available
            ctx = context.copy()
            ctx.update({'states':('assigned',)})
            ctx.update({'what':'out'})
            qty_reserved = prod_obj.get_product_available(cr, uid, [product_id], context=ctx)[product_id]
            available = qty_available + qty_reserved
            difference = qty_available - new_quantity
            if new_quantity is not None and difference > 0 and difference > available:
                move_obj = self.pool['stock.move']
                result['qty_to_unserserve'] = difference - available
                move_ids = move_obj.search(
                    cr, uid,
                    [('product_id', '=', product_id),
                     ('state', '=', 'assigned'),
                     ('picking_id.state', 'in', ('confirmed', 'assigned')),
                     ('type', '=', 'out')], context=context)
                
                for move in move_obj.browse(cr, uid, move_ids, context=context):
                    vals = move_obj._prepare_move_line(cr, uid, move, result['qty_to_unserserve'], context=context)
                    moves_vals.append(vals)
                
            else:
                result['qty_to_unserserve'] = 0.0
        moves_vals = sorted(moves_vals, key=lambda val: val['sequence'])
        result['move_line_ids'] = moves_vals
        return {'value': result}

    def change_product_qty(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        print "oo", context
        prod_obj = self.pool['product.product']
        for data in self.browse(cr, uid, ids, context=context):
            product = data.product_id
            qty_available = product.qty_available
            ctx = context.copy()
            ctx.update({'states':('assigned',)})
            ctx.update({'what':'out'})
            qty_reserved = prod_obj.get_product_available(cr, uid, [product.id], context=ctx)[product.id]
            available = qty_available + qty_reserved
            difference = qty_available - data.new_quantity
            if data.new_quantity is not None and difference > 0 and difference > available:
                print "???"
                qty_to_unreserve = difference - available
                for move_line in data.move_line_ids:
                    print "!!", move_line.sequence
                    
                    if not move_line.to_reassign:
                        continue
                    move_line.move_id.cancel_assign()
                    qty_to_unreserve -= move_line.move_id.product_qty
                    if qty_to_unreserve <= 0.0:
                        break
                else:
                    raise orm.except_orm(_('Error!'),
                          _('You have not selected enought product to unreserve'))
        res = super(StockChangeProductQty, self).change_product_qty(
            cr, uid, ids, context=context)


class MoveLineWizard(orm.TransientModel):
    _inherit = "move.line.wizard"

    _columns = {
        'inventory_wizard_id': fields.many2one('stock.change.product.qty', 'Inventory Wizard'),
    }
            


