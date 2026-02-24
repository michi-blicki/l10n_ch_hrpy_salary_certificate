# -*- coding: utf-8 -*-
{
    'name': 'Swiss Salary Certificate (Payroll)',
    'summary': 'Generate yearly Swiss salary certificates from payroll payslips',
    'description': """
Swiss Salary Certificate module for Odoo 18 Community Edition.

This module provides the technical foundation to generate salary certificates
for employees using configurable field formulas based on payroll payslips.
    """,

    'author': 'Michael Blickenstorfer',
    'website': 'https://www.github.com/michi-blicki/l10n_ch_hrpy_salary_certificate',
    'license': 'AGPL-3',

    'category': 'Payroll Localization',
    'version': '18.0.0.1.0',
    'application': False,
    'auto_install': False,
    'installable': True,

    'depends': [
        'hr',
        'hr_contract',
        'payroll',
        'mail',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/compliance_rule_presets.xml',
        'views/salary_certificate_views.xml',
        'views/salary_certificate_template_views.xml',
        'views/salary_certificate_auxiliary_views.xml',
        'views/hr_employee_views.xml',
        'wizards/import_official_template_wizard_views.xml',
        'wizards/generate_salary_certificate_wizard_views.xml',
        'data/ir_cron.xml',
    ],

    'assets': {

    },

    'translation_files': [

    ],

    'demo': [
        
    ],

    #
    # Hooks
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}

