$(document).ready(function () {
	
	var instance = openerp;
	var qweb = openerp.qweb;
	qweb.add_template('/tbvip/static/src/xml/tbvip_website.xml');

//PAGE: kontra bon

	var kontra_bon_list = [];

	$('#kontra_bon_wrap').each(function () {
		
		var purchase_kontra_bon = this;
		
		function kontra_bon_get_data() {
			$(".website_list_container, #message_container").empty();
			var filters = JSON.stringify({
				'supplier': $("#supplier").val(),
				'state': $("#state").val(),
				'time_range': $("#time_range").val(),
			});
			$.ajax({
				dataType: "json",
				url: '/tbvip/kontra_bon/fetch_data/'+filters,
				method: 'POST',
				success: function(response) {
					var container = $("#message_container");
					if (response.error) {
						MessageDialog.display(container, response.error, "error", 0);
						return;
					}
					if (response.info) {
						MessageDialog.display(container, response.info, "info");
						return;
					}
					$.each(response.data[0], function(key, value) {
						kontra_bon_list[value.id] = value;
					});
					kontra_bon_display_list(response.data);
				},
			});
		}

		function kontra_bon_display_list(data) {
			$("#list_container", purchase_kontra_bon).html(qweb.render('website_tbvip_kontra_bon_list',{
				'kontra': data[0],
				'journals': data[1],
			}));
			$(".rupiah").each(function() {
				var amount = parseFloat($(this).text());
				$(this).text(formatMoney(amount,2,',','.'));
			});
			$(".accordion").click(function(event) {
				$(this).toggleClass("active");
				var detail = $(this).next();
				if (detail.css("maxHeight") != "0px"){
					detail.css("maxHeight", "0px");
				} else {
					detail.css("maxHeight", detail.prop("scrollHeight")+ "px");
				}
			});
		}

		function kontra_bon_save(save_button) {
			Loading.show($('body'));
			var parent_div = save_button.parent().parent();
			var id = parent_div.parent().find("#id").attr("data-id");
			kontra_bon_list[id].reference = parent_div.find("#reference").val();
			kontra_bon_list[id].amount = parent_div.find("#amount").val();
			kontra_bon_list[id].journal_id = parent_div.find("#journal_id").val();
			kontra_bon_list[id].check_maturity_date = parent_div.find("#check_maturity_date").val();

			var json_string = JSON.stringify({
				'id': id,
				'reference': kontra_bon_list[id].reference.length == 0? '' : kontra_bon_list[id].reference,
				'amount': kontra_bon_list[id].amount.length == 0? '' : kontra_bon_list[id].amount,
				'journal_id': kontra_bon_list[id].journal_id.length == 0? '' : kontra_bon_list[id].journal_id,
				'check_maturity_date': kontra_bon_list[id].check_maturity_date.length == 0? null : kontra_bon_list[id].check_maturity_date,
			});
			$.ajax({
				dataType: "json",
				url: '/tbvip/kontra_bon/save/'+json_string,
				method: 'POST',
				success: function(response) {
					alert(response.info);
					Loading.hide();
				},
			});
		}

		function kontra_bon_cancel(cancel_button) {
			var parent_div = cancel_button.parent().parent();
			var id = parent_div.parent().find("#id").attr("data-id");
			parent_div.find("#reference").val(kontra_bon_list[id].reference);
			parent_div.find("#amount").val(kontra_bon_list[id].amount);
			parent_div.find("#journal_id").val(kontra_bon_list[id].journal_id);
			parent_div.find("#check_maturity_date").val(kontra_bon_list[id].check_maturity_date);
		}

	//karena ini list with filter, masukin form filter
		$.get('/tbvip/kontra_bon/fetch_suppliers', null, function(data){
			setTimeout(function() {
				$("#filter_container", purchase_kontra_bon).html(qweb.render('website_tbvip_kontra_bon_filter',{
					'suppliers': JSON.parse(data)
				}));
			},1000)
		});
	
	//handle event di semua kemungkinan div yang muncul
		$(purchase_kontra_bon).on("click", "#btn_filter", function () {
			kontra_bon_get_data();
		});

		$(purchase_kontra_bon).on("click", "#btn_save", function () {
			kontra_bon_save($(this));
		});

		$(purchase_kontra_bon).on("click", "#btn_cancel", function () {
			kontra_bon_cancel($(this));
		});
	});
});

