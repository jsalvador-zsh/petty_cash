# -*- coding: utf-8 -*-
from odoo import fields, models

class PaymentType(models.Model):
    _name = 'payment.type'
    _description = 'Tipo de Pago'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)
    requires_number = fields.Boolean(
        string='Requiere Número', 
        help='Indica si este tipo de pago requiere número de operación'
    )