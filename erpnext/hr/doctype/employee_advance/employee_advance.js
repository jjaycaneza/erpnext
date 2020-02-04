// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Advance', {
	setup: function(frm) {
		frm.add_fetch("employee", "company", "company");
		frm.add_fetch("company", "default_employee_advance_account", "advance_account");

		frm.set_query("employee", function() {
			return {
				filters: {
					"status": "Active"
				}
			};
		});

		frm.set_query("advance_account", function() {
			return {
				filters: {
					"root_type": cur_frm.doc.employee_advance_fund_source == "Not Applicable" ? "Asset" : "Liability",
					"is_group": 0,
					"company": frm.doc.company
				}
			};
		});
	},

	refresh: function(frm) {
		if (frm.doc.docstatus===1
			&& (flt(frm.doc.paid_amount) < flt(frm.doc.advance_amount))
			&& frappe.model.can_create("Payment Entry") && frm.doc.employee_advance_fund_source == "Not Applicable") {
			frm.add_custom_button(__('Payment'),
				function() { frm.events.make_payment_entry(frm); }, __('Create'));
		}
		else if (
			frm.doc.docstatus === 1
			&& (flt(frm.doc.claimed_amount) + flt(frm.doc.returned_money)) < flt(frm.doc.paid_amount)
			&& frappe.model.can_create("Expense Claim")
		) {
			frm.add_custom_button(
				__("Expense Claim"),
				function() {
					frm.events.make_expense_claim(frm);
				},
				__('Create')
			);
		}
	},

	make_payment_entry: function(frm) {
		var method = "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry";
		if(frm.doc.__onload && frm.doc.__onload.make_payment_via_journal_entry) {
			method = "erpnext.hr.doctype.employee_advance.employee_advance.make_bank_entry"
		}
		return frappe.call({
			method: method,
			args: {
				"dt": frm.doc.doctype,
				"dn": frm.doc.name,
				"eas": frm.doc.employee_advance_fund_source
			},
			callback: function(r) {
				console.log(r.message);
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	make_expense_claim: function(frm) {
		return frappe.call({
			method: "erpnext.hr.doctype.expense_claim.expense_claim.get_expense_claim",
			args: {
				"employee_name": frm.doc.employee,
				"company": frm.doc.company,
				"employee_advance_name": frm.doc.name,
				"posting_date": frm.doc.posting_date,
				"paid_amount": frm.doc.paid_amount,
				"claimed_amount": frm.doc.claimed_amount,
				"expense_claim_fund_source": frm.doc.employee_advance_fund_source,
				"returned_money": frm.doc.returned_money,
				"branch": frm.doc.branch,
				"business_units": frm.doc.business_units
			},
			callback: function(r) {
				const doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	employee: function (frm) {
		if (frm.doc.employee) {
			return frappe.call({
				method: "erpnext.hr.doctype.employee_advance.employee_advance.get_due_advance_amount",
				args: {
					"employee": frm.doc.employee,
					"posting_date": frm.doc.posting_date
				},
				callback: function(r) {
					frm.set_value("due_advance_amount",r.message);
				}
			});
		}
	}
});
