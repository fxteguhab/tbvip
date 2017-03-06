from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm

# ==========================================================================================================================

class account_invoice(models.Model):
	_inherit = 'account.invoice'
	
	# METHODS ------------------------------------------------------------------------------------------------

	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	discount_amount = fields.Float(string='Discount')
	check_maturity_date = fields.Date(string='Check Maturity Date',
									  readonly=True, states={'draft': [('readonly', False)]})
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	@api.one
	@api.depends('invoice_line.price_subtotal', 'tax_line.amount', 'discount_amount')
	def _compute_amount(self):
		super(account_invoice, self)._compute_amount()
		if self.amount_total - self.discount_amount < 0:
			raise except_orm('Warning!','Discount should be less than or equals to the subtotal amount.')
		else:
			self.amount_total -= self.discount_amount

# ==========================================================================================================================


class account_invoice_line(models.Model):
	_inherit = 'account.invoice.line'
	
	# METHODS ---------------------------------------------------------------------------------------------------------------
	@api.depends('price_unit', 'discount_amount')
	def _compute_discount_amount_percentage(self):
		"""
		Final price for each line is computed with the equation (self.price_unit*(1-(self.discount or 0.0)/100.0)).
		To make use the discount field, the discount_amount will be converted into percentage, so that the subtotal
		of each line will be updated as expected when there's a change in the field.
		"""
		for record in self:
			if(record.price_unit != 0):
				record.discount = (record.discount_amount / record.price_unit) * 100.0
			else:
				record.discount = 0.0

	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	discount_amount = fields.Float(string='Discount')
	discount = fields.Float(string='Discount (%)', digits= dp.get_precision('Discount'),
							compute=_compute_discount_amount_percentage, default=0.0)
