from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

# ==========================================================================================================================

class account_invoice(models.Model):
	_inherit = 'account.invoice'
	
	# METHODS ------------------------------------------------------------------------------------------------

	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	discount_amount = fields.Float(string='Discount Amount')
	check_maturity_date = fields.Date(string='Check Maturity Date',
									  readonly=True, states={'draft': [('readonly', False)]})
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------


# ==========================================================================================================================


class account_invoice_line(models.Model):
	_inherit = 'account.invoice.line'
	
	# METHODS ---------------------------------------------------------------------------------------------------------------
	@api.depends('price_unit', 'discount_amount')
	def _compute_discount_amount_percentage(self):
		self.discount = (self.discount_amount / self.price_unit) * 100.0

	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	discount_amount = fields.Float(string='Discount Amount')
	discount = fields.Float(string='Discount (%)', digits= dp.get_precision('Discount'),
							compute=_compute_discount_amount_percentage, default=0.0)

	# OVERRIDES -------------------------------------------------------------------------------------------------------------
