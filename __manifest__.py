{
    'name': 'Caja Chica',
    'version': '18.0.1.0.0',
    'summary': 'Gestión de Caja Chica, Caja de Distribución y Recibos de Constancia',
    'description': """
        Módulo para la gestión de:
        - Caja Chica
        - Caja de Distribución
        - Caja de Logística
        - Recibos de Constancia por Entrega de Efectivo
        
        Permite llevar un control detallado de ingresos y egresos
        con formato profesional basado en plantillas Excel.
        Incluye sistema de recibos de constancia para documentar
        entregas de efectivo a terceras personas.
    """,
    'author': 'Juan Salvador',
    'category': 'Accounting',
    'depends': [
        'base',
        'web',
        'account',
        'hr',
    ],
    'data': [
        'security/caja_chica_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/payment_types_data.xml',
        'views/caja_chica_views.xml',
        'views/caja_chica_menus.xml',
        'views/distribution_cash_views.xml',
        'views/distribution_cash_menus.xml',
        'views/logistics_cash_views.xml',
        'views/logistics_cash_menus.xml',
        'views/cash_receipt_views.xml',
        'views/cash_receipt_menus.xml',
        'reports/paperformat.xml',
        'reports/peruanita_layout_background_horizontal.xml',
        'reports/receipt_layout.xml',
        'reports/caja_chica_report.xml',
        'reports/distribution_cash_report.xml',
        'reports/cash_receipt_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'petty_cash/static/src/css/caja_chica.css',
            'petty_cash/static/src/js/caja_selection_widget.js',
            'petty_cash/static/src/xml/caja_selection_templates.xml',
            'petty_cash/static/src/css/styles.css',
        ],
        'web.assets_frontend': [
            'petty_cash/static/src/css/caja_chica.css',
        ],
    },
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}