


clean:
	find . -iname \*.pyc -delete


dev-install:
	[ ! -d env/ ] && virtualenv env/ --python=python2.7
	source env/bin/activate
	pip install -r requirements.txt
