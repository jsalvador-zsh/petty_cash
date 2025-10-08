# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class PayInvoiceWizard(models.TransientModel):
    _name = 'pay.invoice.wizard'
    _description = 'Asistente para Pagar Facturas desde Caja'
    
    # Campo para el tipo de caja
    cash_type = fields.Selection([
        ('petty', 'Caja Chica'),
        ('distribution', 'Caja de Distribución'),
        ('logistics', 'Caja de Logística')
    ], string='Tipo de Caja', required=True)
    
    # Campos para cada tipo de caja
    petty_cash_id = fields.Many2one(
        'petty.cash',
        string='Caja Chica',
        domain="[('state', '=', 'open')]"
    )
    
    distribution_cash_id = fields.Many2one(
        'distribution.cash',
        string='Caja de Distribución',
        domain="[('state', '=', 'open')]"
    )
    
    logistics_cash_id = fields.Many2one(
        'logistics.cash',
        string='Caja de Logística',
        domain="[('state', '=', 'open')]"
    )
    
    # Información de la factura
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura a Pagar',
        required=True,
        domain="[('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']), ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial'])]"
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Proveedor/Cliente',
        related='invoice_id.partner_id',
        readonly=True
    )
    
    amount_residual = fields.Monetary(
        string='Saldo Pendiente',
        related='invoice_id.amount_residual',
        readonly=True
    )
    
    amount = fields.Monetary(
        string='Monto a Pagar',
        required=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='invoice_id.currency_id',
        readonly=True
    )
    
    date = fields.Date(
        string='Fecha de Pago',
        required=True,
        default=fields.Date.context_today
    )
    
    description = fields.Text(
        string='Descripción',
        compute='_compute_description',
        store=True,
        readonly=False
    )
    
    # Campos computados para validación
    cash_balance = fields.Float(
        string='Saldo de Caja',
        compute='_compute_cash_balance'
    )
    
    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """Autocompletar monto con el saldo de la factura"""
        if self.invoice_id:
            self.amount = self.invoice_id.amount_residual
    
    @api.depends('invoice_id', 'partner_id')
    def _compute_description(self):
        """Generar descripción automática"""
        for wizard in self:
            if wizard.invoice_id and wizard.partner_id:
                wizard.description = f"Pago de {wizard.invoice_id.name} - {wizard.partner_id.name}"
            else:
                wizard.description = ''
    
    @api.depends('cash_type', 'petty_cash_id', 'distribution_cash_id', 'logistics_cash_id')
    def _compute_cash_balance(self):
        """Obtener saldo de la caja seleccionada"""
        for wizard in self:
            if wizard.cash_type == 'petty' and wizard.petty_cash_id:
                wizard.cash_balance = wizard.petty_cash_id.current_balance
            elif wizard.cash_type == 'distribution' and wizard.distribution_cash_id:
                wizard.cash_balance = wizard.distribution_cash_id.current_balance
            elif wizard.cash_type == 'logistics' and wizard.logistics_cash_id:
                wizard.cash_balance = wizard.logistics_cash_id.current_balance
            else:
                wizard.cash_balance = 0.0
    
    @api.constrains('amount', 'amount_residual')
    def _check_amount(self):
        """Validar que el monto no exceda el saldo de la factura"""
        for wizard in self:
            if wizard.amount <= 0:
                raise UserError("El monto a pagar debe ser mayor a cero.")
            if wizard.amount > wizard.amount_residual:
                raise UserError(
                    f"El monto a pagar ({wizard.amount}) no puede ser mayor "
                    f"al saldo pendiente de la factura ({wizard.amount_residual})."
                )
    
    def action_pay_invoice(self):
        """Crear línea de pago en la caja correspondiente"""
        self.ensure_one()
        
        # Validar que se haya seleccionado una caja
        if self.cash_type == 'petty' and not self.petty_cash_id:
            raise UserError("Debe seleccionar una Caja Chica.")
        elif self.cash_type == 'distribution' and not self.distribution_cash_id:
            raise UserError("Debe seleccionar una Caja de Distribución.")
        elif self.cash_type == 'logistics' and not self.logistics_cash_id:
            raise UserError("Debe seleccionar una Caja de Logística.")
        
        # Validar saldo de caja
        if self.amount > self.cash_balance:
            raise UserError(
                f"Saldo insuficiente en la caja. "
                f"Saldo disponible: {self.cash_balance}, Monto a pagar: {self.amount}"
            )
        
        # Preparar valores de la línea
        line_vals = {
            'date': self.date,
            'line_type': 'expense',
            'invoice_id': self.invoice_id.id,
            'partner_id': self.partner_id.id,
            'partner_name': self.partner_id.name,
            'document_type': 'factura' if self.invoice_id.move_type in ['out_invoice', 'in_invoice'] else 'boleta',
            'document_number': self.invoice_id.name,
            'description': self.description,
            'amount': self.amount,
        }
        
        # Crear línea en la caja correspondiente
        if self.cash_type == 'petty':
            line_vals['petty_cash_id'] = self.petty_cash_id.id
            line = self.env['petty.cash.line'].create(line_vals)
            cash = self.petty_cash_id
        elif self.cash_type == 'distribution':
            line_vals['distribution_cash_id'] = self.distribution_cash_id.id
            line = self.env['distribution.cash.line'].create(line_vals)
            cash = self.distribution_cash_id
        else:  # logistics
            line_vals['logistics_cash_id'] = self.logistics_cash_id.id
            line = self.env['logistics.cash.line'].create(line_vals)
            cash = self.logistics_cash_id
        
        # Mensaje de éxito
        message = f"Pago registrado exitosamente. Factura: {self.invoice_id.name}, Monto: {self.amount}"
        if line.payment_id:
            message += f". Pago generado: {line.payment_id.name}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Pago Registrado',
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': cash._name,
                    'res_id': cash.id,
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                }
            }
        }

