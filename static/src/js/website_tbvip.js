
Number.prototype.formatMoney = function(c, d, t){
var n = this, 
    c = isNaN(c = Math.abs(c)) ? 2 : c, 
    d = d == undefined ? "." : d, 
    t = t == undefined ? "," : t, 
    s = n < 0 ? "-" : "", 
    i = parseInt(n = Math.abs(+n || 0).toFixed(c)) + "", 
    j = (j = i.length) > 3 ? j % 3 : 0;
   return s + (j ? i.substr(0, j) + t : "") + i.substr(j).replace(/(\d{3})(?=\d)/g, "$1" + t) + (c ? d + Math.abs(n - i).toFixed(c).slice(2) : "");
 };

$(document).ready(function () {
	
	var message_timer;
	var instance = openerp;
	var qweb = openerp.qweb;
	qweb.add_template('/tbvip/static/src/xml/tbvip_website.xml');

	function display_message(container, message, type='info', timeout=5) { //timeout dalam detik
		var type_to_class = {
			'info': 'oe_callout_info',
			'error': 'oe_callout_danger',
		}
		var type_to_text = {
			'info': 'Info',
			'error': 'Error',
		}
		container.html(
			'<div class="oe_callout '+type_to_class[type]+'">'+
				'<h4>'+type_to_text[type]+'</h4>'+
				'<p>'+message+'</p>'+
			'</div>'
		).fadeIn();
		$("html, body").animate({scrollTop: 0}, 500);
		if (timeout > 0) {
			message_timer = setTimeout(function() {
				clear_message(container);
			},timeout*1000);
		}
	}
	
	function clear_message(container) {
		container.fadeOut().html('');
	}

	function addCommas(nStr) {
        nStr += '';
        x = nStr.split(',');
        x1 = x[0];
        x2 = x.length > 1 ? ',' + x[1] : '';
        var rgx = /(\d+)(\d{3})/;
        while (rgx.test(x1)) {
            x1 = x1.replace(rgx, '$1' + '.' + '$2');
        }
        return x1 + x2;
    }


	$('#kontra_bon_wrap').each(function () {
		
		var purchase_kontra_bon = this;
		var message_container = $("#message_container");
		
		function kontra_bon_get_data() {
			var supplier = $("#supplier").val().toUpperCase();
			var state = $("#state").val();
			var time_range = $("#time_range").val();
            $(".website_list_container").empty();
			$.ajax({
				dataType: "json",
				url: '/tbvip/kontra_bon/fetch_data/'+supplier+'/'+state+'/'+time_range,
				method: 'POST',
				success: function(response) {
					if (response.error) {
						display_message(message_container, response.error, "error", 0);
						return;
					}
					if (response.info) {
						display_message(message_container, response.info, "info");
						return;
					}
					kontra_bon_display_list(response.data);
				},
			});
		}


		function kontra_bon_display_list(data) {
			$("#list_container", purchase_kontra_bon).html(qweb.render('website_tbvip_kontra_bon_list',{
				'kontra': data[0],
				journals: data[1]
			}));
			var accordion = document.getElementsByClassName("accordion");
			var i;

			for (i = 0; i < accordion.length; i++) {
				accordion[i].onclick = function() {
					this.classList.toggle("active");
					var accordionDetail = this.nextElementSibling;
					if (accordionDetail.style.maxHeight){
						accordionDetail.style.maxHeight = null;
					} else {
						accordionDetail.style.maxHeight = accordionDetail.scrollHeight + "px";
					}
				}
			}
            $(".rupiah").each(function() {
                $(this).text("Rp. " + addCommas($(this).text()));
            });
		}

        function kontra_bon_save(save_button) {
            var id = $("#id").attr("data-id");
            var reference = $("#reference").val();
            var amount = $("#amount").val();
            var journal_id = $("#journal_id").val();
            var check_maturity_date = $("#check_maturity_date").val();
            if (reference.length == 0) {
                reference = null;
            }
            if (amount.length == 0) {
                amount = null;
            }
            if (journal_id.length == 0) {
                journal_id = null;
            }
            if (check_maturity_date.length == 0) {
                check_maturity_date = null;
            }
            $.ajax({
                dataType: "json",
                url: '/tbvip/kontra_bon/save/'+id+'/'+reference+'/'+amount+'/'+journal_id+'/'+check_maturity_date,
                method: 'POST',
                success: function(response) {
                    var parent_div = save_button.parent().closest('div');
                    parent_div.find("input").each(function( index ) {
                        $(this).attr("default_value", $(this).attr("value"));
                    })
                    alert("Save Success");
                },
            });
        }

		function kontra_bon_cancel(cancel_button) {
            var parent_div = cancel_button.parent().closest('div');
            parent_div.find("input").each(function( index ) {
                $(this).attr("value", $(this).attr("default_value"));
            })
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

