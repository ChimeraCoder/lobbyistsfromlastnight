check-envars: guard-APP_SETTINGS guard-MONGODB_DATABASE guard-MONGODB_HOST guard-MONGODB_PORT guard-MONGODB_USER guard-MONGODB_PASSWORD guard-MEMCACHE_SERVERS guard-MEMCACHE_USERNAME guard-MEMCACHE_PASSWORD guard-MEMCACHED_HOST guard-MEMCACHED_PORT guard-SUNLIGHT_API_KEY guard-TWILIO_ACCOUNT_SID guard-TWILIO_AUTH_TOKEN guard-TWILIO_OUTGOING PORT guard-APP_DEBUG guard-SESSION_SECRET guard-SUNLIGHT_API_KEY

guard-%:
	@if [ -z ${${*}} ] ; then \
	        echo "Environment variable $* not set"; \
	                exit 1; \
	fi


clean:
	find . -iname \*.pyc -delete
	rm -rf build/


dev-install:
	[ ! -d env/ ] && virtualenv env/ --python=python2.7
	source env/bin/activate
	pip install -r requirements.txt
