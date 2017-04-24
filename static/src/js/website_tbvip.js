$(document).ready(function () {
	
	var instance = openerp;
	var qweb = openerp.qweb;
	qweb.add_template('/tbvip/static/src/xml/tbvip_website_kontra_bon.xml');
	qweb.add_template('/tbvip/static/src/xml/tbvip_website_stock_opname.xml');

//PAGE: KONTRA BON-----------------------------------------------------------------------------------------------------------

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
				//TIMTBVIP: baik berhasil save maupun tidak, tampilkan pesan yang sesuai
				    alert(response.info);
				    if(response.success){
				    	kontra_bon_get_data();
				    }
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


//PAGE: STOCK OPNAME---------------------------------------------------------------------------------------------------------

		var stock_opname_list = [];

		$('#stock_opname_wrap').each(function () {

			var stock_opname = this;

			function stock_opname_get_data() {
				$("#so_message_container").empty();
				var filters = JSON.stringify({
					'branch': $("#so_branch").val(),
					'state': $("#so_state").val(),
					'employee': $("#so_employee").val(),
					'product': $("#so_product").val(),
				});
				$.ajax({
					dataType: "json",
					url: '/tbvip/stock_opname/fetch_data/'+filters,
					method: 'POST',
					success: function(response) {
						var container = $("#so_message_container");
						if (response.error) {
							MessageDialog.display(container, response.error, "error", 0);
							return;
						}
						if (response.info) {
							MessageDialog.display(container, response.info, "info");
							return;
						}
						$.each(response.data, function(key, value) {
							stock_opname_list[value.id] = value;
						});
						stock_opname_display_list(response.data);
					},
				});
			}

			function so_inject_get_data() {
				$.get('/tbvip/stock_opname/fetch_so_inject', null, function(data){
					var data_parsed = JSON.parse(data)
					$("#so_inject_list_container", stock_opname).html(qweb.render('website_tbvip_so_inject_list',{
						'so_inject_list': JSON.parse(data_parsed['so_inject_list'])
					}));
					$("#so_inject_input_container", stock_opname).html(qweb.render('website_tbvip_so_inject_input',{
						'products': JSON.parse(data_parsed['products']),
					}));
				});
			}

			function stock_opname_display_list(data) {
				$("#so_list_container", stock_opname).html(qweb.render('website_tbvip_stock_opname_list',{
					'stock_opname_list': data,
				}));
			}

			function so_inject_save(save_button) {
				Loading.show($('body'));
				var parent_div = save_button.parent().parent();
				var product_name = parent_div.parent().find("#product").val();
				var priority = parent_div.parent().find("#priority").val();
				var json_string = JSON.stringify({
					'product_name': product_name,
					'priority': priority,
				});
				$.ajax({
					dataType: "json",
					url: '/tbvip/stock_opname/create_so_inject/'+json_string,
					method: 'POST',
					success: function(response) {
						alert(response.info);
						if(response.success){
							so_inject_get_data();
							if ($(".accordion_so_inject_list").hasClass("active")) {
								$(".accordion_so_inject_list").click();
							}
						}
						Loading.hide();
					},
				});
			}

			$.get('/tbvip/stock_opname/fetch_so_data', null, function(data){
				var data_parsed = JSON.parse(data)
				$("#so_filter_container", stock_opname).html(qweb.render('website_tbvip_stock_opname_filter',{
					'branches': JSON.parse(data_parsed['branches']),
					'employees': JSON.parse(data_parsed['employees']),
					'products': JSON.parse(data_parsed['products']),
				}));
			});
			so_inject_get_data()

		//handle event di semua kemungkinan div yang muncul
			$(stock_opname).on("click", "#so_btn_filter", function () {
				stock_opname_get_data();
			});

			$(stock_opname).on("click", "#so_inject_btn_save", function () {
				so_inject_save($(this));
			});

			$(stock_opname).on("click", ".accordion", function () {
				$(this).toggleClass("active");
				var detail = $(this).next();
				if (detail.css("maxHeight") != "0px"){
					detail.css("maxHeight", "0px");
				} else {
					detail.css("maxHeight", detail.prop("scrollHeight")+ "px");
				}
			});
		});
});

