raw_events = null;
event_table_cid = null;

function loadEventListings(cid, events){
	raw_events = events;
	fillEventsTable(cid, raw_events, true);
	event_table_cid=cid;
}

function fillEventsTable(cid, events, push_event_to_top){
	var hash = document.location.hash.substring(1);

	var event_table_body = document.getElementById('event_table_body');
	event_table_body.innerHTML = "";
	if(push_event_to_top){
		for(var i=0; i < events.length; i++){
			var e = events[i];
			if(event_id == e['id']){
				appendEventToTable(event_table_body, e);
			}
		}
	}
	for(var i=0; i < events.length; i++){
		var e = events[i];
		if(event_id == e['id']){
			if(push_event_to_top){
				continue;
			}
		}
		appendEventToTable(event_table_body, e, cid);
	}
}

function appendEventToTable(table, e, cid){
	var event_row = document.createElement('tr');
	event_row.setAttribute('id', 'event_' + e['id']);
	if(event_id == e['id']){
		event_row.className = 'event_row_highlighted';
	}
	var href = "<a name='"+e['id']+"'></a>";
	appendCellToRow(event_row, e['start_date'], 'date');
	appendCellToRow(event_row, e['entertainment'], 'event');
	appendCellToRow(event_row, e['venue'], 'location');
	appendCellToRow(event_row, e['hosts'], 'hosts');
	appendCellToRow(event_row, e['contributions_info'], 'contributions');
	var event_html = '<a href="http://politicalpartytime.org/party/' + e['id'] + '/" target="_blank">More Info &raquo;</a>';
	appendCellToRow(event_row, event_html, 'event_listing');
	var tweet_html = '<a href="#" onclick="displayTweetOverlay(\''+cid+'\', \''+e['id']+'\'); return false;">Tweet &raquo;</a>';
	appendCellToRow(event_row, tweet_html, 'suggested_tweets');
	table.appendChild(event_row);
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
	fillEventsTable(event_table_cid, events, false);
}

function getBitlyUrl(eventUrl) {
	var xmlHttp = new XMLHttpRequest();
        var apiUrl = "http://api.bitly.com/v3/shorten?apikey=R_9a6bd171e9c54f2216d31f9ecbab7f36&login=o_7hnnbv3ima&uri=" + eventUrl;
	xmlHttp.open( "GET", apiUrl, false );
	xmlHttp.send( null );
	var response =  JSON.parse(xmlHttp.responseText);
        var bitlyUrl = response.data.url;

	return bitlyUrl;
}

function displayTweetOverlay(cid, eventId){
	var wrapper = document.getElementById("tweet_overlay_wrapper");
	wrapper.style.display = 'block';
	wrapper.onclick = function(){
		wrapper.style.display = 'none';
	}
	var thisEvent;
	for(var i=0; i < raw_events.length; i++){
		var e = raw_events[i];
		if(e['id'] == eventId){
			thisEvent = e;
			break;
		}
	}
        var eventUrl = "http://www.lobbyistsfromlastnight.com/events/" + cid + "/" + eventId;
	// var eventUrl = 'http://' + location.hostname;
	// if(location.port){
	//	eventUrl += ':' + location.port;
	//}
	//eventUrl += location.pathname + '/' + eventId;
        bitlyUrl = getBitlyUrl(eventUrl);

	var listElt = document.getElementById("tweet_overlay_list");
	listElt.innerHTML = "";
	for(var i=0; i < thisEvent['suggested_tweets'].length; i++){
		var tweet = thisEvent['suggested_tweets'][i];
                tweet = tweet.replace("/link/", bitlyUrl);
		var tweetElt = document.createElement('div');
		tweetElt.className = 'tweet_overlay_elt';
		tweetElt.innerHTML = '<a href="https://twitter.com/intent/tweet?text=' + encodeURIComponent(tweet) + ' "class="twitter-share-button" data-count="none" data-lang="en" data-size="large">' + tweet + '</a>';
		listElt.appendChild(tweetElt);
	}
	var newTweetElt = document.createElement('div');
	newTweetElt.className = 'tweet_overlay_elt';
	newTweetElt.innerHTML = '<a href="https://twitter.com/intent/tweet?text=' + encodeURIComponent(' #lfln ' + bitlyUrl + '/') + ' "class="twitter-share-button" data-count="none" data-lang="en" data-size="large">Write your own!</a>';
	listElt.appendChild(newTweetElt);

	document.getElementById('tweet_overlay_close').onclick = function(){
		wrapper.style.display = 'none';
	}
}



