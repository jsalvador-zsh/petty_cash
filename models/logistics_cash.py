from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date

class LogisticsCash(models.Model):
    _name = 'logistics.cash'
    _description = 'Caja de Logística'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos básicos
    name = fields.Char(
        string='Número',
        copy=False,
        readonly=True,
        default='Borrador'
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
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario Contable',
        domain="[('type', 'in', ['cash', 'bank'])]",
        required=True,
        help='Diario contable asociado a esta caja'
    )
    
    initial_payment_type_id = fields.Many2one(
        'payment.type',
        string='Tipo de Pago Inicial'
    )

    initial_operation_number = fields.Char(
        string='Número de Operación/Cheque',
        help='Número de operación bancaria, cheque u otro documento'
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
        'logistics.cash.line',
        'logistics_cash_id',
        string='Movimientos'
    )
    
    # Contabilidad
    move_id = fields.Many2one(
        'account.move',
        string='Asiento Contable',
        readonly=True,
        help='Asiento contable generado al abrir la caja'
    )
    
    closing_move_id = fields.Many2one(
        'account.move',
        string='Asiento de Cierre',
        readonly=True,
        help='Asiento contable generado al cerrar la caja'
    )
    
    # Campo calculado para mostrar nombre
    display_name = fields.Char(
        string='Nombre para Mostrar',
        compute='_compute_display_name',
        store=True
    )

    @api.model
    def create(self, vals):
        """Crear registro en borrador sin secuencia"""
        # No asignar secuencia en la creación, usar 'Borrador'
        if 'name' not in vals or not vals.get('name'):
            vals['name'] = 'Borrador'
        return super(LogisticsCash, self).create(vals)

    def _get_next_sequence(self):
        """Obtener la siguiente secuencia disponible"""
        return self.env['ir.sequence'].next_by_code('logistics.cash') or 'LOG/001'

    @api.depends('name', 'date', 'responsible_id', 'state')
    def _compute_display_name(self):
        for record in self:
            if record.state == 'draft':
                record.display_name = f"Borrador - {record.date} ({record.responsible_id.name})"
            else:
                record.display_name = f"{record.name} - {record.date} ({record.responsible_id.name})"

    @api.depends('line_ids.amount', 'initial_amount')
    def _compute_totals(self):
        for record in self:
            income_lines = record.line_ids.filtered(lambda l: l.line_type == 'income')
            expense_lines = record.line_ids.filtered(lambda l: l.line_type == 'expense')
            
            record.total_income = sum(income_lines.mapped('amount')) + record.initial_amount
            record.total_expense = sum(expense_lines.mapped('amount'))
            record.current_balance = record.total_income - record.total_expense

    # ========== VALIDACIONES ==========
    
    @api.constrains('initial_amount')
    def _check_initial_amount(self):
        for record in self:
            if record.initial_amount < 0:
                raise ValidationError("El monto inicial no puede ser negativo.")

    @api.constrains('state', 'initial_amount')
    def _check_open_requirements(self):
        for record in self:
            if record.state == 'open' and record.initial_amount <= 0:
                raise ValidationError(
                    "No se puede abrir una caja sin un monto inicial mayor a cero. "
                    f"Monto actual: {record.initial_amount}"
                )

    @api.constrains('current_balance', 'state')
    def _check_close_requirements(self):
        for record in self:
            if record.state == 'closed' and record.current_balance < 0:
                raise ValidationError(
                    "No se puede cerrar una caja con saldo negativo. "
                    f"Saldo actual: {record.current_balance}"
                )

    # ========== MÉTODOS DE ACCIÓN ==========

    def _create_opening_move(self):
        """Crear asiento contable de apertura de caja"""
        self.ensure_one()
        if not self.journal_id:
            raise UserError("Debe seleccionar un diario contable para la caja.")
        
        cash_account = self.journal_id.default_account_id
        if not cash_account:
            raise UserError(f"El diario {self.journal_id.name} no tiene una cuenta por defecto configurada.")
        
        company = self.company_id
        counterpart_account = company.account_journal_suspense_account_id
        if not counterpart_account:
            raise UserError("No se ha configurado una cuenta de suspense en la compañía.")
        
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': f'Apertura {self.name}',
            'line_ids': [
                (0, 0, {
                    'name': f'Apertura de {self.name} - Monto Inicial',
                    'account_id': cash_account.id,
                    'debit': self.initial_amount,
                    'credit': 0.0,
                    'partner_id': False,
                }),
                (0, 0, {
                    'name': f'Apertura de {self.name} - Monto Inicial',
                    'account_id': counterpart_account.id,
                    'debit': 0.0,
                    'credit': self.initial_amount,
                    'partner_id': False,
                }),
            ],
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        return move

    def action_open(self):
        """Abrir caja con validaciones y asignar secuencia"""
        for record in self:
            if record.initial_amount <= 0:
                raise UserError(
                    f"No se puede abrir la caja {record.name}. "
                    "El monto inicial debe ser mayor a cero."
                )
            if record.state != 'draft':
                raise UserError(f"Solo se pueden abrir cajas en estado borrador.")
            
            # Asignar secuencia al abrir la caja
            if record.name == 'Borrador':
                record.name = record._get_next_sequence()
            
            # Crear asiento contable de apertura
            opening_move = record._create_opening_move()
            
            record.write({
                'state': 'open',
                'move_id': opening_move.id
            })
            record.message_post(
                body=f"Caja de Logística {record.name} abierta con monto inicial: {record.initial_amount}. Asiento contable: {opening_move.name}",
                message_type='notification'
            )

    def _create_closing_move(self):
        """Crear asiento contable de cierre de caja"""
        self.ensure_one()
        if not self.journal_id:
            raise UserError("Debe seleccionar un diario contable para la caja.")
        
        if self.current_balance == 0:
            return False
        
        cash_account = self.journal_id.default_account_id
        if not cash_account:
            raise UserError(f"El diario {self.journal_id.name} no tiene una cuenta por defecto configurada.")
        
        company = self.company_id
        counterpart_account = company.account_journal_suspense_account_id
        if not counterpart_account:
            raise UserError("No se ha configurado una cuenta de suspense en la compañía.")
        
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': f'Cierre {self.name}',
            'line_ids': [
                (0, 0, {
                    'name': f'Cierre de {self.name} - Devolución de saldo',
                    'account_id': cash_account.id,
                    'debit': 0.0,
                    'credit': self.current_balance,
                    'partner_id': False,
                }),
                (0, 0, {
                    'name': f'Cierre de {self.name} - Devolución de saldo',
                    'account_id': counterpart_account.id,
                    'debit': self.current_balance,
                    'credit': 0.0,
                    'partner_id': False,
                }),
            ],
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        return move

    def action_close(self):
        """Cerrar caja con validaciones"""
        for record in self:
            if record.state != 'open':
                raise UserError("Solo se pueden cerrar cajas abiertas.")
            if record.current_balance < 0:
                raise UserError(
                    f"No se puede cerrar la caja {record.name} con saldo negativo. "
                    f"Saldo actual: {record.current_balance}"
                )
            
            # Crear asiento contable de cierre si hay saldo
            closing_move = record._create_closing_move()
            
            vals = {'state': 'closed'}
            if closing_move:
                vals['closing_move_id'] = closing_move.id
                
            record.write(vals)
            
            message = f"Caja de Logística {record.name} cerrada con saldo final: {record.current_balance}"
            if closing_move:
                message += f". Asiento de cierre: {closing_move.name}"
            
            record.message_post(
                body=message,
                message_type='notification'
            )

    def action_cancel(self):
        """Cancelar caja con validaciones"""
        for record in self:
            if record.state == 'closed':
                raise UserError("No se puede cancelar una caja que ya está cerrada.")
            
            record.write({'state': 'cancelled'})
            record.message_post(
                body=f"Caja de Logística {record.name} cancelada",
                message_type='notification'
            )

    def action_reset_to_draft(self):
        """Restablecer a borrador con validaciones"""
        for record in self:
            if record.state == 'closed':
                raise UserError("No se puede restablecer a borrador una caja cerrada.")
            
            # Restablecer a 'Borrador' si se vuelve a draft
            record.write({
                'state': 'draft',
                'name': 'Borrador'
            })
            record.message_post(
                body=f"Caja de Logística restablecida a borrador",
                message_type='notification'
            )
        
    def action_recalculate_balances(self):
        """Método para recalcular todos los saldos de las líneas"""
        for record in self:
            if record.state == 'closed':
                raise UserError("No se pueden recalcular saldos en una caja cerrada.")
            
            for line in record.line_ids.sorted('sequence'):
                line._compute_balance()
        return True

    # ========== RESTRICCIONES DE ELIMINACIÓN ==========
    
    def unlink(self):
        """Prevenir eliminación de cajas abiertas o cerradas"""
        for record in self:
            if record.state in ('open', 'closed'):
                raise UserError(
                    f"No se puede eliminar la caja {record.name} en estado '{record.state}'. "
                    "Solo se pueden eliminar cajas en estado 'borrador' o 'cancelada'."
                )
        return super(LogisticsCash, self).unlink()

    # ========== OTROS MÉTODOS ==========

    @api.model
    def action_logistics_cash_monthly(self):
        first_day = date.today().replace(day=1)
        return {
            "type": "ir.actions.act_window",
            "name": "Resumen Mensual Logística",
            "res_model": "logistics.cash",
            "view_mode": "list,kanban,form",
            "domain": [("date", ">=", first_day)],
            "context": {
                "search_default_current_month": 1,
                "group_by": ["responsible_id"],
            },
        }
    
class LogisticsCashLine(models.Model):
    _name = 'logistics.cash.line'
    _description = 'Línea de Caja de Logística'
    _order = 'sequence, date desc, id desc'

    # Relación principal
    logistics_cash_id = fields.Many2one(
        'logistics.cash',
        string='Caja de Logística',
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
        ('orden_compra', 'Orden de Compra'),
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
    
    # Campos para integración contable
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura',
        domain="[('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']), ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial'])]",
        help='Factura del sistema que se está pagando con esta línea'
    )
    
    payment_id = fields.Many2one(
        'account.payment',
        string='Pago Generado',
        readonly=True,
        help='Pago generado en el sistema al registrar este movimiento'
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Asiento Contable',
        readonly=True,
        help='Asiento contable generado para este movimiento'
    )

    # ========== VALIDACIONES PARA LÍNEAS ==========
    
    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount <= 0:
                raise ValidationError("El monto debe ser mayor a cero.")

    @api.constrains('logistics_cash_id')
    def _check_cash_state(self):
        for line in self:
            if line.logistics_cash_id.state == 'closed':
                raise ValidationError(
                    "No se pueden agregar o modificar movimientos en una caja cerrada."
                )

    # ========== MÉTODOS COMPUTADOS ==========

    @api.depends('partner_id')
    def _compute_partner_name(self):
        for line in self:
            if line.partner_id:
                line.partner_name = line.partner_id.name
            elif not line.partner_name:
                line.partner_name = ''

    @api.depends('logistics_cash_id.line_ids.amount', 'sequence', 'amount', 'line_type')
    def _compute_balance(self):
        for line in self:
            if not line.logistics_cash_id:
                line.balance = 0.0
                continue
                
            # Obtener todas las líneas anteriores ordenadas
            previous_lines = line.logistics_cash_id.line_ids.filtered(
                lambda l: l.sequence < line.sequence or (l.sequence == line.sequence and l != line)
            ).sorted('sequence')
            
            # Calcular saldo acumulado
            balance = line.logistics_cash_id.initial_amount
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
    
    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """Autocompletar información de la factura"""
        if self.invoice_id:
            self.partner_id = self.invoice_id.partner_id
            self.amount = self.invoice_id.amount_residual
            self.document_type = 'factura' if self.invoice_id.move_type in ['out_invoice', 'in_invoice'] else 'boleta'
            self.document_number = self.invoice_id.name
            self.description = f"Pago de {self.invoice_id.name} - {self.invoice_id.partner_id.name}"
            self.line_type = 'expense'
    
    def _create_line_move(self):
        """Crear asiento contable para el movimiento"""
        self.ensure_one()
        
        if self.logistics_cash_id.state != 'open':
            return False
        
        if self.move_id:
            return self.move_id
        
        cash_account = self.logistics_cash_id.journal_id.default_account_id
        if not cash_account:
            raise UserError(f"El diario {self.logistics_cash_id.journal_id.name} no tiene una cuenta por defecto configurada.")
        
        if self.partner_id:
            if self.line_type == 'expense':
                counterpart_account = self.partner_id.property_account_payable_id
            else:
                counterpart_account = self.partner_id.property_account_receivable_id
        else:
            company = self.logistics_cash_id.company_id
            counterpart_account = company.account_journal_suspense_account_id
        
        if not counterpart_account:
            raise UserError("No se pudo determinar la cuenta de contrapartida para el movimiento.")
        
        line_vals = []
        if self.line_type == 'expense':
            line_vals = [
                (0, 0, {
                    'name': self.description or 'Egreso de caja',
                    'account_id': counterpart_account.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                }),
                (0, 0, {
                    'name': self.description or 'Egreso de caja',
                    'account_id': cash_account.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'partner_id': False,
                }),
            ]
        else:
            line_vals = [
                (0, 0, {
                    'name': self.description or 'Ingreso de caja',
                    'account_id': cash_account.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'partner_id': False,
                }),
                (0, 0, {
                    'name': self.description or 'Ingreso de caja',
                    'account_id': counterpart_account.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                }),
            ]
        
        move_vals = {
            'journal_id': self.logistics_cash_id.journal_id.id,
            'date': self.date,
            'ref': f'{self.logistics_cash_id.name} - {self.description[:50] if self.description else "Movimiento"}',
            'line_ids': line_vals,
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        self.move_id = move.id
        return move
    
    def _create_payment_for_invoice(self):
        """Crear pago para factura enlazada"""
        self.ensure_one()
        
        if not self.invoice_id:
            return False
        
        if self.payment_id:
            return self.payment_id
        
        payment_type = 'outbound' if self.invoice_id.move_type in ['in_invoice', 'out_refund'] else 'inbound'
        partner_type = 'supplier' if self.invoice_id.move_type in ['in_invoice', 'out_refund'] else 'customer'
        
        payment_vals = {
            'payment_type': payment_type,
            'partner_type': partner_type,
            'partner_id': self.invoice_id.partner_id.id,
            'amount': self.amount,
            'date': self.date,
            'journal_id': self.logistics_cash_id.journal_id.id,
            'memo': f'{self.logistics_cash_id.name} - Pago {self.invoice_id.name}',
        }
        
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()
        
        # Conciliar el pago con la factura
        # En Odoo 18, accedemos a las líneas a través del asiento contable
        if payment.move_id:
            payment_lines = payment.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') 
                and not l.reconciled
            )
            invoice_lines = self.invoice_id.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') 
                and not l.reconciled
            )
            
            lines_to_reconcile = payment_lines + invoice_lines
            if lines_to_reconcile:
                lines_to_reconcile.reconcile()
        
        self.payment_id = payment.id
        return payment
    
    @api.model
    def create(self, vals):
        """Override create para generar asientos automáticamente"""
        line = super(LogisticsCashLine, self).create(vals)
        
        if line.logistics_cash_id.state == 'open':
            if line.invoice_id:
                line._create_payment_for_invoice()
            else:
                line._create_line_move()
        
        return line

    # ========== RESTRICCIONES DE ELIMINACIÓN PARA LÍNEAS ==========
    
    def unlink(self):
        """Prevenir eliminación de líneas en cajas cerradas"""
        for line in self:
            if line.logistics_cash_id.state == 'closed':
                raise UserError(
                    f"No se pueden eliminar movimientos de la caja {line.logistics_cash_id.name} "
                    "porque está cerrada."
                )
        return super(LogisticsCashLine, self).unlink()