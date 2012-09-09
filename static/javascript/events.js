raw_events = null;

function loadEventListings(events){
	raw_events = events;
	fillEventsTable(raw_events);
}
function fillEventsTable(events){
	var event_table_body = document.getElementById('event_table_body');
	event_table_body.innerHTML = "";
	for(var i=0; i < events.length; i++){
		var e = events[i];
		var event_row = document.createElement('tr');
		appendCellToRow(event_row, e['start_date'], 'date');
		appendCellToRow(event_row, e['entertainment'], 'event');
		appendCellToRow(event_row, e['venue'], 'location');
		appendCellToRow(event_row, e['hosts'], 'hosts');
		appendCellToRow(event_row, e['contributions_info'], 'contributions');
		appendCellToRow(event_row, e['suggested_tweets'], 'suggested_tweets');
		event_html = '<a href="http://politicalpartytime.org/party/' + e['id'] + '/" target="_blank">More Info &raquo;</a>';
		appendCellToRow(event_row, event_html, 'event_listing');
		event_table_body.appendChild(event_row);
	}
}
function appendCellToRow(row, cell_html, className){
	var cell = document.createElement('td');
	cell.className = className;
	cell.innerHTML = cell_html;
	row.appendChild(cell);
}
function events_sort_by(sort_key, ascending, is_date, is_numeric){
	events = raw_events.sort(function(a,b){
		var a_value = a[sort_key];
		var b_value = b[sort_key];

		if(a_value && a_value.length > 0 && (!b_value || b_value.length == 0) ) {
			return -1;
		}else if( (!a_value || a_value.length == 0) && b_value && b_value.length > 0){
			return 1;
		}

		if(is_numeric){
			a_results = a_value.match(/\$([0-9\,\.]+?)[^\,0-9\.]+/);
			if(a_results){
				a_value = a_results[1];
				a_value = a_value.replace(',','');
				a_value = parseInt(a_value);
				// alert(a[sort_key] + " -> " + a_value);
			}else{
				a_value = 0;
			}

			b_results = b_value.match(/\$([0-9\,\.]+?)[^\,0-9\.]+/);
			if(b_results){	
				b_value = b_results[1];
				b_value = b_value.replace(',','');
				b_value = parseInt(b_value);
			}else{
				b_value = 0;
			}
		}
		if(is_date){
			a_value = Date.parse(a_value);
			b_value = Date.parse(b_value);
		}
		if(a_value < b_value){
			return ascending ? -1 : 1;
		}else if(a_value > b_value){
			return ascending ? 1 : -1;
		}else{
			return 0;
		}
	}) 
	fillEventsTable(events)
}
