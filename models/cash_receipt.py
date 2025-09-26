from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date

class CashReceipt(models.Model):
    _name = 'cash.receipt'
    _description = 'Recibo de Constancia por Entrega de Efectivo'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos básicos
    name = fields.Char(
        string='Número de Recibo',
        copy=False,
        readonly=True,
        default='Borrador'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        readonly=True
    )
    
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    # Área que genera (debe ir antes para usar en validaciones)
    area = fields.Selection([
        ('logistica', 'Logística'),
        ('admin_gerencia', 'Administración Gerencia')
    ], string='Área que Genera', required=True, tracking=True,
       help='Área de la empresa que genera el recibo')
    
    # Personas involucradas
    partner_id = fields.Many2one(
        'res.partner',
        string='Persona que Recibe',
        tracking=True,
        help='Persona que recibe el efectivo (requerido solo para Admin. Gerencia)'
    )
    
    created_by_id = fields.Many2one(
        'res.users',
        string='Creado por',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
        help='Usuario que crea el recibo'
    )
    
    # Información financiera
    amount = fields.Float(
        string='Monto Entregado',
        required=True,
        tracking=True,
        help='Monto en efectivo entregado'
    )
    
    # Campos descriptivos
    concept = fields.Text(
        string='Concepto',
        tracking=True,
        help='Descripción del motivo de la entrega de efectivo (requerido solo para Admin. Gerencia)'
    )
    
    # Estados
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)
    
    # Campo calculado para mostrar nombre
    display_name = fields.Char(
        string='Nombre para Mostrar',
        compute='_compute_display_name',
        store=True
    )
    
    # Campos adicionales
    notes = fields.Text(
        string='Observaciones',
        help='Notas adicionales sobre la entrega'
    )
    
    # Campos de moneda (para mostrar el total formateado)
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )

    @api.model
    def create(self, vals):
        """Crear registro en borrador sin secuencia"""
        # No asignar secuencia en la creación, usar 'Borrador'
        if 'name' not in vals or not vals.get('name'):
            vals['name'] = 'Borrador'
        return super(CashReceipt, self).create(vals)

    def _get_next_sequence(self):
        """Obtener la siguiente secuencia para el recibo"""
        return self.env['ir.sequence'].next_by_code('cash.receipt') or 'REC/001'

    @api.depends('name', 'date', 'partner_id', 'state')
    def _compute_display_name(self):
        for record in self:
            if record.state == 'draft':
                if record.partner_id:
                    record.display_name = f"Borrador - {record.partner_id.name} - {record.date}"
                else:
                    record.display_name = f"Borrador - {record.date}"
            else:
                if record.partner_id:
                    record.display_name = f"{record.name} - {record.partner_id.name} - {record.date}"
                else:
                    record.display_name = f"{record.name} - {record.date}"

    # ========== VALIDACIONES ==========
    
    @api.constrains('amount')
    def _check_amount(self):
        """Validar que el monto sea positivo"""
        for record in self:
            if record.amount <= 0:
                raise ValidationError("El monto entregado debe ser mayor a cero.")

    @api.constrains('date')
    def _check_date(self):
        """Validar que la fecha no sea futura"""
        for record in self:
            if record.date > fields.Date.today():
                raise ValidationError("La fecha del recibo no puede ser futura.")

    @api.constrains('partner_id', 'concept', 'area', 'state')
    def _check_required_fields_by_area(self):
        """Validar campos requeridos según el área solo al confirmar"""
        for record in self:
            if record.state == 'confirmed' and record.area == 'admin_gerencia':
                if not record.partner_id:
                    raise ValidationError(
                        "Para recibos de Administración Gerencia, "
                        "el campo 'Persona que Recibe' es obligatorio."
                    )
                if not record.concept:
                    raise ValidationError(
                        "Para recibos de Administración Gerencia, "
                        "el campo 'Concepto' es obligatorio."
                    )

    # ========== MÉTODOS DE ACCIÓN ==========

    def action_confirm(self):
        """Confirmar el recibo y asignar secuencia"""
        for record in self:
            if record.state != 'draft':
                raise UserError("Solo se pueden confirmar recibos en estado borrador.")
            
            # Validar campos requeridos según el área antes de confirmar
            if record.area == 'admin_gerencia':
                if not record.partner_id:
                    raise UserError(
                        "Para confirmar un recibo de Administración Gerencia, "
                        "debe especificar la 'Persona que Recibe'."
                    )
                if not record.concept:
                    raise UserError(
                        "Para confirmar un recibo de Administración Gerencia, "
                        "debe especificar el 'Concepto'."
                    )
            
            # Asignar secuencia al confirmar el recibo
            if record.name == 'Borrador':
                record.name = record._get_next_sequence()
            
            record.write({'state': 'confirmed'})
            record.message_post(
                body=f"Recibo {record.name} confirmado por {self.env.user.name}",
                message_type='notification'
            )

    def action_cancel(self):
        """Cancelar el recibo"""
        for record in self:
            if record.state == 'cancelled':
                raise UserError("El recibo ya está cancelado.")
            
            record.write({'state': 'cancelled'})
            record.message_post(
                body=f"Recibo {record.name} cancelado por {self.env.user.name}",
                message_type='notification'
            )

    def action_reset_to_draft(self):
        """Restablecer a borrador"""
        for record in self:
            if record.state == 'draft':
                raise UserError("El recibo ya está en estado borrador.")
            
            # Restablecer a 'Borrador' si se vuelve a draft
            record.write({
                'state': 'draft',
                'name': 'Borrador'
            })
            record.message_post(
                body=f"Recibo restablecido a borrador por {self.env.user.name}",
                message_type='notification'
            )

    # ========== RESTRICCIONES DE ELIMINACIÓN ==========
    
    def unlink(self):
        """Prevenir eliminación de recibos confirmados"""
        for record in self:
            if record.state == 'confirmed':
                raise UserError(
                    f"No se puede eliminar el recibo {record.name} porque está confirmado. "
                    "Cancélelo primero si es necesario."
                )
        return super(CashReceipt, self).unlink()

    # ========== MÉTODOS ADICIONALES ==========

    @api.onchange('area')
    def _onchange_area(self):
        """Limpiar campos no requeridos al cambiar área"""
        if self.area == 'logistica':
            # Para logística, los campos no son requeridos, pero se pueden mantener si ya están llenos
            pass
        elif self.area == 'admin_gerencia':
            # Para admin gerencia, mostrar advertencia si están vacíos
            if not self.partner_id or not self.concept:
                return {
                    'warning': {
                        'title': 'Campos Requeridos',
                        'message': 'Para Administración Gerencia, los campos "Persona que Recibe" y "Concepto" son obligatorios antes de confirmar.'
                    }
                }

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Actualizar información al cambiar el partner"""
        if self.partner_id and not self.partner_id.is_company:
            # Si es una persona física, todo correcto
            pass
        elif self.partner_id and self.partner_id.is_company:
            # Advertencia si es una empresa
            return {
                'warning': {
                    'title': 'Advertencia',
                    'message': 'Ha seleccionado una empresa. Asegúrese de que sea correcto o seleccione una persona física.'
                }
            }

    def get_area_display(self):
        """Obtener el nombre completo del área"""
        area_dict = dict(self._fields['area'].selection)
        return area_dict.get(self.area, '')

    def get_partner_display(self):
        """Obtener el nombre del partner o un texto por defecto"""
        if self.partner_id:
            return self.partner_id.name
        else:
            return "BENEFICIARIO"

    def get_concept_display(self):
        """Obtener el concepto o un texto por defecto"""
        if self.concept:
            return self.concept
        else:
            return "ENTREGA DE EFECTIVO"

    def amount_to_words(self):
        """Convertir el monto a palabras en español"""
        try:
            amount = int(self.amount)
            decimals = int((self.amount - amount) * 100)
            
            # Números básicos
            unidades = ["", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
            decenas = ["", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
            especiales = ["DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
            centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]
            
            def convertir_hasta_999(num):
                if num == 0:
                    return ""
                elif num == 100:
                    return "CIEN"
                elif num < 10:
                    return unidades[num]
                elif num < 20:
                    return especiales[num - 10]
                elif num < 100:
                    d = num // 10
                    u = num % 10
                    if u == 0:
                        return decenas[d]
                    else:
                        return decenas[d] + " Y " + unidades[u]
                else:
                    c = num // 100
                    resto = num % 100
                    resultado = centenas[c]
                    if resto > 0:
                        if resto < 10:
                            resultado += " " + unidades[resto]
                        elif resto < 20:
                            resultado += " " + especiales[resto - 10]
                        else:
                            d = resto // 10
                            u = resto % 10
                            if u == 0:
                                resultado += " " + decenas[d]
                            else:
                                resultado += " " + decenas[d] + " Y " + unidades[u]
                    return resultado
            
            if amount == 0:
                return "CERO SOLES"
            
            # Convertir miles
            if amount < 1000:
                palabras = convertir_hasta_999(amount)
            elif amount < 1000000:
                miles = amount // 1000
                resto = amount % 1000
                if miles == 1:
                    palabras = "MIL"
                else:
                    palabras = convertir_hasta_999(miles) + " MIL"
                
                if resto > 0:
                    palabras += " " + convertir_hasta_999(resto)
            else:
                millones = amount // 1000000
                resto = amount % 1000000
                if millones == 1:
                    palabras = "UN MILLÓN"
                else:
                    palabras = convertir_hasta_999(millones) + " MILLONES"
                
                if resto >= 1000:
                    miles = resto // 1000
                    resto_final = resto % 1000
                    if miles > 0:
                        if miles == 1:
                            palabras += " MIL"
                        else:
                            palabras += " " + convertir_hasta_999(miles) + " MIL"
                    if resto_final > 0:
                        palabras += " " + convertir_hasta_999(resto_final)
                elif resto > 0:
                    palabras += " " + convertir_hasta_999(resto)
            
            # Agregar centavos si existen
            if decimals > 0:
                return palabras + " SOLES CON " + str(decimals).zfill(2) + "/100"
            else:
                return palabras + " SOLES"
                
        except:
            return f"MONTO: {self.amount:.2f} SOLES"

    @api.model
    def get_receipts_by_period(self, date_from, date_to):
        """Obtener recibos por período"""
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'confirmed')
        ]
        return self.search(domain)

    @api.model
    def get_total_amount_by_area(self, area, date_from=None, date_to=None):
        """Obtener total por área en un período"""
        domain = [('area', '=', area), ('state', '=', 'confirmed')]
        
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
            
        receipts = self.search(domain)
        return sum(receipts.mapped('amount'))