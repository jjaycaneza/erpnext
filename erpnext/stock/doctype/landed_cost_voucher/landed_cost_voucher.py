# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt
from frappe.model.meta import get_field_precision
from frappe.model.document import Document
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

class LandedCostVoucher(Document):
	def get_items_from_purchase_receipts(self):
		self.set("items", [])
		for pr in self.get("purchase_receipts"):
			if pr.receipt_document_type and pr.receipt_document:
				pr_items = frappe.db.sql("""select pr_item.item_code, pr_item.description,
					pr_item.qty, pr_item.base_rate, pr_item.base_amount, pr_item.name, pr_item.cost_center,pr_item.business_units,pr_item.branch,pr_item.cost_center
					from `tab{doctype} Item` pr_item where parent = %s
					and exists(select name from tabItem where name = pr_item.item_code and is_stock_item = 1)
					""".format(doctype=pr.receipt_document_type), pr.receipt_document, as_dict=True)

				for d in pr_items:
					item = self.append("items")
					item.item_code = d.item_code
					item.description = d.description
					item.qty = d.qty
					item.rate = d.base_rate
					item.cost_center = d.cost_center or \
						erpnext.get_default_cost_center(self.company)
					item.amount = d.base_amount
					item.receipt_document_type = pr.receipt_document_type
					item.receipt_document = pr.receipt_document
					item.purchase_receipt_item = d.name
					item.business_units = d.business_units
					item.branch = d.branch
					item.cost_center = d.cost_center

	def validate(self):
		self.check_mandatory()
		self.validate_purchase_receipts()
		# self.set_total_taxes_and_charges()
		if not self.get("items"):
			self.get_items_from_purchase_receipts()
		else:
			#WILL BE CHANGED CAUSE WILL BASE ON APPLICABLE CHARGES AND NOT TAX AND CHARGES
			self.validate_applicable_charges_for_item()


	def check_mandatory(self):
		if not self.get("purchase_receipts"):
			frappe.throw(_("Please enter Receipt Document"))


	def validate_purchase_receipts(self):
		receipt_documents = []

		for d in self.get("purchase_receipts"):
			if frappe.db.get_value(d.receipt_document_type, d.receipt_document, "docstatus") != 1:
				frappe.throw(_("Receipt document must be submitted"))
			else:
				receipt_documents.append(d.receipt_document)

		for item in self.get("items"):
			if not item.receipt_document:
				frappe.throw(_("Item must be added using 'Get Items from Purchase Receipts' button"))
			elif item.receipt_document not in receipt_documents:
				frappe.throw(_("Item Row {0}: {1} {2} does not exist in above '{1}' table")
					.format(item.idx, item.receipt_document_type, item.receipt_document))

			if not item.cost_center:
				frappe.throw(_("Row {0}: Cost center is required for an item {1}")
					.format(item.idx, item.item_code))

	def set_total_taxes_and_charges(self):
		self.total_taxes_and_charges = sum([flt(d.amount) for d in self.get("taxes")])

	def validate_applicable_charges_for_item(self):
		if (self.landed_cost_voucher_type == "Update Fresh Goods Price"):
			pass
		else:
			based_on = self.distribute_charges_based_on.lower()

			total = sum([flt(d.get(based_on)) for d in self.get("items")])

			if not total:
				frappe.throw(_("Total {0} for all items is zero, may be you should change 'Distribute Charges Based On'").format(based_on))

			total_applicable_charges = sum([flt(d.applicable_charges) for d in self.get("items")])

			precision = get_field_precision(frappe.get_meta("Landed Cost Item").get_field("applicable_charges"),
			currency=frappe.get_cached_value('Company',  self.company,  "default_currency"))

			diff = flt(self.total_taxes_and_charges) - flt(total_applicable_charges)
			diff = flt(diff, precision)

			if abs(diff) < (2.0 / (10**precision)):
				self.items[-1].applicable_charges += diff
			else:
				frappe.throw(_("Total Applicable Charges in Purchase Receipt Items table must be same as Total Taxes and Charges"))



	def on_submit(self):
		self.update_landed_cost()

	def on_cancel(self):
		self.update_landed_cost()

	def update_landed_cost(self):
		for d in self.get("purchase_receipts"):
			doc = frappe.get_doc(d.receipt_document_type, d.receipt_document)

			# set landed cost voucher amount in pr item
			doc.set_landed_cost_voucher_amount()

			# set valuation amount in pr item
			doc.update_valuation_rate("items")

			# db_update will update and save landed_cost_voucher_amount and voucher_amount in PR
			for item in doc.get("items"):
				item.db_update()

			# update latest valuation rate in serial no
			self.update_rate_in_serial_no(doc)
			
			# update stock & gl entries for cancelled state of PR
			doc.docstatus = 2


			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)

			doc.make_gl_entries_on_cancel(repost_future_gle=False)


			# update stock & gl entries for submit state of PR
			doc.docstatus = 1


			doc.expense_account_custom = "Hiiiiii"

			doc.update_stock_ledger(via_landed_cost_voucher=True)
			doc.make_gl_entries()
			self.update_last_purchase_rate()
			self.update_item_price_in_price()


	def update_rate_in_serial_no(self, receipt_document):
		for item in receipt_document.get("items"):
			if item.serial_no:
				serial_nos = get_serial_nos(item.serial_no)
				if serial_nos:
					frappe.db.sql("update `tabSerial No` set purchase_rate=%s where name in ({0})"
						.format(", ".join(["%s"]*len(serial_nos))), tuple([item.valuation_rate] + serial_nos))



	#OWN SCRIPTS
	def update_last_purchase_rate(self):
		for item in self.items:
			item = item.as_dict()
			print("BUANNGGGG")
			print(item)
			try:
				frappe.db.sql("UPDATE `tabItem` SET last_purchase_rate = %s WHERE name = %s",(item['updated_rate'],item['item_code']),as_dict=True)

				frappe.msgprint("All good")
			except:
				frappe.throw("Er")
	def update_item_price_in_price(self):
		for item in self.items:
			item = item.as_dict()
			print("BUANNGGGG Update sa PR")
			print(item)
			try:
				frappe.db.sql("UPDATE `tabPurchase Receipt Item` SET rate = %s WHERE parent = %s",(item['updated_rate'],item['receipt_document']),as_dict=True)
				po_number = frappe.db.sql("SELECT po_number from `tabPurchase Receipt` WHERE name = %s AND docstatus = 1",( item['receipt_document']),as_dict=True)
				frappe.db.sql("UPDATE `tabPurchase Order Item` SET rate = %s WHERE parent = %s",
							  (item['updated_rate'], po_number[0]['po_number']), as_dict=True)
				frappe.msgprint("All good")
			except:
				frappe.throw("Er")