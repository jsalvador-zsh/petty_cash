from odoo import http, fields
from odoo.http import request
import json


class CajaChicaController(http.Controller):

    @http.route('/petty_cash/dashboard_data', type='json', auth='user')
    def get_dashboard_data(self):
        """Obtener datos para el dashboard de caja chica"""
        user = request.env.user
        CajaChica = request.env['petty.cash']
        
        # Estadísticas del usuario actual
        my_cajas = CajaChica.search([('responsible_id', '=', user.id)])
        open_cajas = my_cajas.filtered(lambda c: c.state == 'open')
        
        data = {
            'total_cajas': len(my_cajas),
            'open_cajas': len(open_cajas),
            'total_balance': sum(open_cajas.mapped('current_balance')),
            'monthly_cajas': len(my_cajas.filtered(
                lambda c: c.date.month == fields.Date.today().month
            ))
        }
        
        return data

    @http.route('/petty_cash/quick_stats', type='json', auth='user')
    def get_quick_stats(self):
        """Estadísticas rápidas para el widget de selección"""
        CajaChica = request.env['petty.cash']
        
        # Contar cajas por estado
        domain_base = [('responsible_id', '=', request.env.user.id)]
        
        stats = {
            'draft': CajaChica.search_count(domain_base + [('state', '=', 'draft')]),
            'open': CajaChica.search_count(domain_base + [('state', '=', 'open')]),
            'closed': CajaChica.search_count(domain_base + [('state', '=', 'closed')]),
            'total': CajaChica.search_count(domain_base)
        }
        
        # Saldo total de cajas abiertas
        open_cajas = CajaChica.search(domain_base + [('state', '=', 'open')])
        stats['total_balance'] = sum(open_cajas.mapped('current_balance'))
        
        return stats

    @http.route('/petty_cash/create_quick', type='json', auth='user')
    def create_quick_caja(self, **kwargs):
        """Crear una caja chica rápidamente"""
        try:
            CajaChica = request.env['petty.cash']
            
            vals = {
                'responsible_id': request.env.user.id,
                'initial_amount': kwargs.get('initial_amount', 0.0),
                'state': 'draft'
            }
            
            caja = CajaChica.create(vals)
            
            return {
                'success': True,
                'caja_id': caja.id,
                'name': caja.name,
                'message': f'Caja Chica {caja.name} creada exitosamente'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ========== CONTROLADORES PARA CAJA DE DISTRIBUCIÓN ==========

    @http.route('/distribution_cash/dashboard_data', type='json', auth='user')
    def get_distribution_dashboard_data(self):
        """Obtener datos para el dashboard de caja de distribución"""
        user = request.env.user
        DistributionCash = request.env['distribution.cash']
        
        # Estadísticas del usuario actual
        my_cajas = DistributionCash.search([('responsible_id', '=', user.id)])
        open_cajas = my_cajas.filtered(lambda c: c.state == 'open')
        
        data = {
            'total_cajas': len(my_cajas),
            'open_cajas': len(open_cajas),
            'total_balance': sum(open_cajas.mapped('current_balance')),
            'monthly_cajas': len(my_cajas.filtered(
                lambda c: c.date.month == fields.Date.today().month
            ))
        }
        
        return data

    @http.route('/distribution_cash/quick_stats', type='json', auth='user')
    def get_distribution_quick_stats(self):
        """Estadísticas rápidas para caja de distribución"""
        DistributionCash = request.env['distribution.cash']
        
        # Contar cajas por estado
        domain_base = [('responsible_id', '=', request.env.user.id)]
        
        stats = {
            'draft': DistributionCash.search_count(domain_base + [('state', '=', 'draft')]),
            'open': DistributionCash.search_count(domain_base + [('state', '=', 'open')]),
            'closed': DistributionCash.search_count(domain_base + [('state', '=', 'closed')]),
            'total': DistributionCash.search_count(domain_base)
        }
        
        # Saldo total de cajas abiertas
        open_cajas = DistributionCash.search(domain_base + [('state', '=', 'open')])
        stats['total_balance'] = sum(open_cajas.mapped('current_balance'))
        
        return stats

    @http.route('/distribution_cash/create_quick', type='json', auth='user')
    def create_quick_distribution(self, **kwargs):
        """Crear una caja de distribución rápidamente"""
        try:
            DistributionCash = request.env['distribution.cash']
            
            vals = {
                'responsible_id': request.env.user.id,
                'initial_amount': kwargs.get('initial_amount', 0.0),
                'state': 'draft'
            }
            
            caja = DistributionCash.create(vals)
            
            return {
                'success': True,
                'caja_id': caja.id,
                'name': caja.name,
                'message': f'Caja de Distribución {caja.name} creada exitosamente'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ========== CONTROLADORES PARA CAJA DE LOGÍSTICA ==========

    @http.route('/logistics_cash/dashboard_data', type='json', auth='user')
    def get_logistics_dashboard_data(self):
        """Obtener datos para el dashboard de caja de logística"""
        user = request.env.user
        LogisticsCash = request.env['logistics.cash']
        
        # Estadísticas del usuario actual
        my_cajas = LogisticsCash.search([('responsible_id', '=', user.id)])
        open_cajas = my_cajas.filtered(lambda c: c.state == 'open')
        
        data = {
            'total_cajas': len(my_cajas),
            'open_cajas': len(open_cajas),
            'total_balance': sum(open_cajas.mapped('current_balance')),
            'monthly_cajas': len(my_cajas.filtered(
                lambda c: c.date.month == fields.Date.today().month
            ))
        }
        
        return data

    @http.route('/logistics_cash/quick_stats', type='json', auth='user')
    def get_logistics_quick_stats(self):
        """Estadísticas rápidas para caja de logística"""
        LogisticsCash = request.env['logistics.cash']
        
        # Contar cajas por estado
        domain_base = [('responsible_id', '=', request.env.user.id)]
        
        stats = {
            'draft': LogisticsCash.search_count(domain_base + [('state', '=', 'draft')]),
            'open': LogisticsCash.search_count(domain_base + [('state', '=', 'open')]),
            'closed': LogisticsCash.search_count(domain_base + [('state', '=', 'closed')]),
            'total': LogisticsCash.search_count(domain_base)
        }
        
        # Saldo total de cajas abiertas
        open_cajas = LogisticsCash.search(domain_base + [('state', '=', 'open')])
        stats['total_balance'] = sum(open_cajas.mapped('current_balance'))
        
        return stats

    @http.route('/logistics_cash/create_quick', type='json', auth='user')
    def create_quick_logistics(self, **kwargs):
        """Crear una caja de logística rápidamente"""
        try:
            LogisticsCash = request.env['logistics.cash']
            
            vals = {
                'responsible_id': request.env.user.id,
                'initial_amount': kwargs.get('initial_amount', 0.0),
                'state': 'draft'
            }
            
            caja = LogisticsCash.create(vals)
            
            return {
                'success': True,
                'caja_id': caja.id,
                'name': caja.name,
                'message': f'Caja de Logística {caja.name} creada exitosamente'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }