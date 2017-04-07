
var formatMoney = function(n, c, d, t){
var c = isNaN(c = Math.abs(c)) ? 2 : c, 
		d = d == undefined ? "." : d, 
		t = t == undefined ? "," : t, 
		s = n < 0 ? "-" : "", 
		i = parseInt(n = Math.abs(+n || 0).toFixed(c)) + "", 
		j = (j = i.length) > 3 ? j % 3 : 0;
	 return s + (j ? i.substr(0, j) + t : "") + i.substr(j).replace(/(\d{3})(?=\d)/g, "$1" + t) + (c ? d + Math.abs(n - i).toFixed(c).slice(2) : "");
 };

var MessageDialog = {

	message_timer: null,
	current_container: null,

	display: function(container, message, type='info', timeout=5) { //timeout dalam detik
		this.current_container = container;
		var self = this;
		var type_to_class = {
			'info': 'oe_callout_info',
			'error': 'oe_callout_danger',
		}
		var type_to_text = {
			'info': 'Info',
			'error': 'Error',
		}
	//HTML sengaja di sini dan bukan di qweb supaya object ini modular dan bisa dipakai 
	//di project manapun yang punya website module
		this.current_container.html(
			'<div class="oe_callout '+type_to_class[type]+'">'+
				'<h4>'+type_to_text[type]+'</h4>'+
				'<p>'+message+'</p>'+
			'</div>'
		).fadeIn();
		$("html, body").animate({scrollTop: 0}, 500);
		if (timeout > 0) {
			this.message_timer = setTimeout(function() {
				self.clear();
			},timeout*1000);
		}
	},
	
	clear: function() {
		this.current_container.fadeOut().html('');
	}

}

var Loading = {
	show: function(container) {
		container.append(
			'<div class="loading_div">' +
				'<div class="loader blockUI blockOverlay"/>' +
			'</div>'
		);
	},
	hide: function() {
		$(".loading_div").remove();
	}
}

