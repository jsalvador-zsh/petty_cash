from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class DistributionCash(models.Model):
    _name = 'distribution.cash'
    _description = 'Caja de Distribución'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos básicos
    name = fields.Char(
        string='Número',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self._get_next_sequence()
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today
    )
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsable',
        required=True,
        default=lambda self: self.env.user
    )
    
    # Información financiera
    initial_amount = fields.Float(
        string='Monto Inicial',
        required=True,
        default=0.0
    )
    total_income = fields.Float(
        string='Total Ingresos',
        compute='_compute_totals',
        store=True
    )
    total_expense = fields.Float(
        string='Total Egresos',
        compute='_compute_totals',
        store=True
    )
    current_balance = fields.Float(
        string='Saldo Actual',
        compute='_compute_totals',
        store=True
    )
    
    # Estados
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('open', 'Abierta'),
        ('closed', 'Cerrada'),
        ('cancelled', 'Cancelada')
    ], string='Estado', default='draft', tracking=True)
    
    # Relaciones
    line_ids = fields.One2many(
        'distribution.cash.line',
        'distribution_cash_id',
        string='Movimientos'
    )
    
    # Campo calculado para mostrar nombre
    display_name = fields.Char(
        string='Nombre para Mostrar',
        compute='_compute_display_name',
        store=True
    )

    @api.model
    def _get_next_sequence(self):
        return self.env['ir.sequence'].next_by_code('distribution.cash') or 'DIST/001'

    @api.depends('name', 'date', 'responsible_id')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} - {record.date} ({record.responsible_id.name})"

    @api.depends('line_ids.amount', 'initial_amount')
    def _compute_totals(self):
        for record in self:
            income_lines = record.line_ids.filtered(lambda l: l.line_type == 'income')
            expense_lines = record.line_ids.filtered(lambda l: l.line_type == 'expense')
            
            record.total_income = sum(income_lines.mapped('amount')) + record.initial_amount
            record.total_expense = sum(expense_lines.mapped('amount'))
            record.current_balance = record.total_income - record.total_expense

    def action_open(self):
        self.state = 'open'

    def action_close(self):
        if self.current_balance < 0:
            raise ValidationError("No se puede cerrar una caja de distribución con saldo negativo.")
        self.state = 'closed'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset_to_draft(self):
        self.state = 'draft'
        
    def action_recalculate_balances(self):
        """Método para recalcular todos los saldos de las líneas"""
        for line in self.line_ids.sorted('sequence'):
            line._compute_balance()
        return True

    @api.model
    def action_distribution_cash_monthly(self):
        first_day = date.today().replace(day=1)
        return {
            "type": "ir.actions.act_window",
            "name": "Resumen Mensual Distribución",
            "res_model": "distribution.cash",
            "view_mode": "list,kanban,form",
            "domain": [("date", ">=", first_day)],
            "context": {
                "search_default_current_month": 1,
                "group_by": ["responsible_id"],
            },
        }
    
class DistributionCashLine(models.Model):
    _name = 'distribution.cash.line'
    _description = 'Línea de Caja de Distribución'
    _order = 'sequence, date desc, id desc'

    # Relación principal
    distribution_cash_id = fields.Many2one(
        'distribution.cash',
        string='Caja de Distribución',
        required=True,
        ondelete='cascade'
    )
    
    # Campos de control
    sequence = fields.Integer(string='Secuencia', default=10)
    
    # Información básica
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today
    )
    area_id = fields.Many2one(
        'hr.department',
        string='Área'
    )
    
    # Tipo de movimiento
    line_type = fields.Selection([
        ('income', 'Ingreso'),
        ('expense', 'Egreso')
    ], string='Tipo', required=True, default='expense')
    
    # Documento
    document_type = fields.Selection([
        ('factura', 'Factura'),
        ('boleta', 'Boleta'),
        ('recibo', 'Recibo'),
        ('ticket', 'Ticket'),
        ('guia_remision', 'Guía de Remisión'),
        ('otros', 'Otros')
    ], string='Tipo Documento')
    document_number = fields.Char(string='Número Documento')
    
    # Proveedor/Beneficiario
    partner_id = fields.Many2one(
        'res.partner',
        string='Proveedor/Beneficiario'
    )
    partner_name = fields.Char(
        string='Nombre Proveedor',
        compute='_compute_partner_name',
        store=True,
        readonly=False
    )
    
    # Descripción y monto
    description = fields.Text(string='Descripción', required=True)
    amount = fields.Float(string='Monto', required=True)
    
    # Saldo acumulado
    balance = fields.Float(
        string='Saldo',
        compute='_compute_balance',
        store=True
    )
    
    # Campos adicionales para control
    notes = fields.Text(string='Observaciones')
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Adjuntos'
    )

    @api.depends('partner_id')
    def _compute_partner_name(self):
        for line in self:
            if line.partner_id:
                line.partner_name = line.partner_id.name
            elif not line.partner_name:
                line.partner_name = ''

    @api.depends('distribution_cash_id.line_ids.amount', 'sequence', 'amount', 'line_type')
    def _compute_balance(self):
        for line in self:
            if not line.distribution_cash_id:
                line.balance = 0.0
                continue
                
            # Obtener todas las líneas anteriores ordenadas
            previous_lines = line.distribution_cash_id.line_ids.filtered(
                lambda l: l.sequence < line.sequence or (l.sequence == line.sequence and l != line)
            ).sorted('sequence')
            
            # Calcular saldo acumulado
            balance = line.distribution_cash_id.initial_amount
            for prev_line in previous_lines:
                if prev_line == line:
                    break
                if prev_line.line_type == 'income':
                    balance += prev_line.amount
                else:
                    balance -= prev_line.amount

            # Incluir la línea actual
            if line.line_type == 'income':
                balance += line.amount
            else:
                balance -= line.amount

            line.balance = balance

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_name = self.partner_id.name