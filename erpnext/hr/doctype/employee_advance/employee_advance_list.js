/**
 * Created by shiela on 12/3/19.
 */
frappe.listview_settings['Employee Advance'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == "Paid") {
			return [__("Paid"), "orange", "status,=,'Paid'"];
		}else if(doc.status == "Unpaid") {
			return [__("Unpaid"), "red"];
		} else if(doc.status == "Claimed") {
			return [__("Claimed"), "green"];
		} else if(doc.status == "Unliquidated") {
			return [__("Unliquidated"), "red"];
		} else if(doc.status == "Liquidated") {
			return [__("Liquidated"), "green"];
		} else if(doc.status == "Partially Liquidated") {
			return [__("Partially Liquidated"), "orange"];
		}
	}
};
