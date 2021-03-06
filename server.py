#! /usr/bin/env python

from __future__ import division, print_function
from flask import Flask
from flask import request, redirect, url_for
from flask import Response
from flask import render_template
from flask import flash
from flask import jsonify
from flask.ext.login import LoginManager, login_required, UserMixin, current_user
from functools import wraps
import os
import sunlight
import json
import time
import urllib2
import csv
import re
import pylibmc
import parsedatetime as pdt
import phonenumbers

app = Flask(__name__)
app.config.from_envvar('APP_SETTINGS')
app.secret_key = app.config["SESSION_SECRET"]

from werkzeug.contrib.cache import MemcachedCache

cache = MemcachedCache(['127.0.0.1:11211'])

from flask.ext.wtf import Form, TextField, PasswordField, validators, BooleanField

###HACK THAT FIXES PYMONGO BUG
#http://stackoverflow.com/questions/10401499/mongokit-importerror-no-module-named-objectid-error
#TODO remove this once the upstream bug is fixed
import sys 
import pymongo
import bson.objectid
pymongo.objectid = bson.objectid
sys.modules["pymongo.objectid"] = bson.objectid
pymongo.binary = bson.binary
sys.modules["pymongo.binary"] = bson.binary
#### END HACK THAT WILL BE REMOVED

cache = pylibmc.Client(servers=[app.config['MEMCACHE_SERVERS']], binary=True)
cache = MemcachedCache(cache)

from flaskext.mongoalchemy import MongoAlchemy, BaseQuery
db = MongoAlchemy(app)

MEMCACHED_TIMEOUT = 10 * 60
MEMCACHED_TIMEOUT_SUNLIGHT = 3 * 60 * 60


MAX_SEARCH_RESULTS = 20

ROMNEY_CID = 'N00000286'
OBAMA_CID = 'N00009638'

sunlight.config.API_KEY = app.config['SUNLIGHT_API_KEY']

login_manager = LoginManager()
login_manager.setup_app(app)

from twilio.rest import TwilioRestClient
client = TwilioRestClient()


import logging
from logging import Formatter, FileHandler
file_handler = FileHandler('runlogs.log', mode='a')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
        ))
app.logger.addHandler(file_handler)

@app.route('/')
def welcome():
    return render_template("home.html")

@app.route('/twitter')
def twitter():
    return render_template("twitter.html")

@app.route('/about/')
def about():
    return render_template("about.html")

@app.route('/contact/')
def contact():
    return render_template("contact.html")

#This is called *after* the user's password is verified
#TODO remove the redundant second query and combine it with the first
@login_manager.user_loader
def load_user(userid):
    #TODO check passwords!
    print("loading user", userid)

    #check the memcached cache first
    rv = cache.get(userid)
    if rv is None:
        rv = MongoUser.query.filter(MongoUser.mongo_id == userid).first()
        if rv is not None:
            cache.set(userid, rv, MEMCACHED_TIMEOUT)
    return rv

def load_user_by_username(username):
    user_result = MongoUser.query.filter(MongoUser.username == username).first()
   
    if user_result is not None:
        cache.set(str(user_result.mongo_id), user_result, MEMCACHED_TIMEOUT)

    return user_result


@app.route('/login/', methods = ["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        #login and validate user
        login_user(form.user)
        flash("Logged in successfully")
        return redirect(request.args.get("next") or url_for("legislators_search"))
    else:

        return render_template("login.html", form=form)


@app.route('/signup/', methods = ["GET" , "POST"])
def signup():
    form = RegistrationForm()
    if form.validate_on_submit():
        print("registering user")
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        confirm = request.form['confirm']
        zipcode = request.form['zipcode']
        accept_tos = request.form['accept_tos']
        new_user = MongoUser(username = username, password = bcrypt.hashpw(password, bcrypt.gensalt()), email = email, zipcode=zipcode, created_at = int(time.time()))
        new_user.save()
        return redirect(url_for('welcome'))
    else:
        return render_template("signup.html", form=form)

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for('welcome'))




@login_manager.unauthorized_handler
def unauthorized():
    return render_template("index.html", flash="unauthorized", intro_text="You need to log in to view this page")

       
@app.context_processor
def inject_user_authenticated():
    return dict(user_authenticated = current_user.is_authenticated())
   

class SMSSubscription(db.Document):
    phone_number = db.StringField()
    legislator_id = db.StringField() #The same one that is used for the /events/<cid> route

class MongoUser(db.Document, UserMixin):
    username = db.StringField()
    password = db.StringField()
    zipcode = db.StringField()
    email = db.StringField()
    created_at = db.IntField(required = True)
    
    def get_id(self):
        return str(self.mongo_id)

class RegistrationForm(Form):
    username = TextField('Username', [validators.Length(min=4, max=25)])
    email = TextField('Email Address', [validators.Length(min=6, max=35)])
    zipcode = TextField('Zipcode', [validators.Length(min=5, max=35)])
    password = PasswordField('New Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match')
        ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the TOS', [validators.Required()])

class LoginForm(Form):
    username = TextField('Username', [validators.Required()])
    password = PasswordField('Password', [validators.Required()])

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        #TODO check password
        user = MongoUser.query.filter(MongoUser.username == self.username.data).first()

        if user is None:
            return False
        else:
            #self.username = user.username
            entered_password = self.password.data
            if bcrypt.hashpw(entered_password, user.password) == user.password:
                #User entered the correct password
                cache.set(user.get_id(), user, MEMCACHED_TIMEOUT)
                self.user = user
                return True
            else:
                return False


@app.route('/events/<cid>/')
@app.route('/events/<cid>/<eid>/')
def events_for_legislator(cid, eid=None):
    person = person_by_cid(cid)
    events = events_by_cid(cid)
    event_count = len(events)
    for event in events:
        event['suggested_tweets'] = suggested_tweets(person, event)
    events = json.dumps(events, default=lambda o: o.__dict__)

    title = person['title'] + ' ' + person['lastname'] + ' | Events'
    return render_template('events.html', events=events, person=person, event_count=event_count, event_id=eid, title=title, cid=cid)

def events_by_cid(cid):
     #check the memcached cache first
    cache_key = "events_" + cid
    events = cache.get(cache_key)
    breakcache = request.args.get("breakcache", None) 
    if events is None or breakcache is not None:
        try:
            events = json.loads(urllib2.urlopen("http://politicalpartytime.org/json/" + cid).read())
            if events is not None:
                cache.set(cache_key, events, MEMCACHED_TIMEOUT_SUNLIGHT)
        except urllib2.URLError:
            events = []

    for e in events:
        e['fields']['id'] = e['pk']
    events = map(lambda e: e['fields'], events)

    # print(events)
    # for e in events:
    #     if e['start_date']:
    # 	   e['start_date'] = time.strptime(e['start_date'], "%Y-%m-%d")
    #        print(e['start_date'])
    #        print(e['start_date'].tm_year)
    # events.sort(key=lambda e: e['start_date'].tm_year)
    for e in events:
        if e['start_date']:
           e['start_date'] = time.strptime(e['start_date'], "%Y-%m-%d")
           e['start_date'] = time.strftime("%b %d, %Y", e['start_date'])
    # events.reverse()
    return events   

def parse_tweet(tweet, event, person):
    '''Will return None if an error occurs'''

   #person will likely be a legislator
    if tweet is "":
        return None

    try:
        tweet = tweet.replace("@lawmaker",  "@"+person['twitter_id'])
    except TypeError:
        return None

    contribution_regex = re.compile("\$[\d,]+")
    if event['contributions_info']:
        contribution_matches = contribution_regex.match(event['contributions_info'])
        if contribution_matches:
            contribution_amount = contribution_matches.group()
            tweet.replace("[Contributions Info]", contribution_amount)

    tweet = tweet.replace("[venue name]", "venue")
    tweet = tweet.replace("[start time]", "start_time")
    if event.has_key("end_time"):
        tweet = tweet.replace("[end time]", "end_time")
    tweet = tweet.replace("[event date]", "start_date")
    tweet = tweet + " #lfln"

    if "[" in tweet:
        return None
    return tweet

def suggested_tweets(legislator, event):

    #If a null legislator is provided, return an empty list
    if legislator is None:
        return []

    suggested_tweets = []
    tweets_csv = csv.reader(open('tweets.tsv', 'rb'), delimiter='\t')
    for row in tweets_csv:
        keyword = row[0].lower()
        if event['entertainment'] == None:
            continue
        if keyword in event['entertainment'].lower():
	    for tweet in row[1:]:
                suggested_tweets.append(parse_tweet(tweet, event, legislator))
        elif keyword == 'obama' and legislator['lastname'] == 'Obama':
            for tweet in row[1:]:
                suggested_tweets.append(parse_tweet(tweet, event, legislator))
        elif keyword == 'romney' and legislator['lastname'] == 'Romney':
            for tweet in row[1:]:
                suggested_tweets.append(parse_tweet(tweet, event, legislator))
        elif keyword == 'general':
            for tweet in row[1:]:
                suggested_tweets.append(parse_tweet(tweet, event, legislator))

    #Filter out all None (null) tweets
    suggested_tweets = filter(lambda x: x is not None, suggested_tweets)
    return suggested_tweets

def telephone_by_cid(cid):
    person = person_by_cid(cid);
    return person.get('phone', None)        

def person_by_cid(cid):
    #check the memcached cache first
    cache_key = "person_" + cid
    person = cache.get(cache_key)
    breakcache = request.args.get("breakcache", None) 
    if person is None or breakcache is not None:
        people = sunlight.congress.legislators(crp_id=cid)
        if people and len(people) > 0:
            person = people[0]
        else:
            if cid == OBAMA_CID:
                person = {
                    'title' : 'President',
                    'firstname' : 'Barack',
                    'middlename' : 'Hussein',
                    'lastname' : 'Obama',
                    'party' : 'D',
                    'twitter_id' : 'BarackObama',
                    'phone' : '202-456-1111'
                }
            elif cid == ROMNEY_CID:
                person = {
                    'title' : 'Governor',
                    'firstname' : 'Willard',
                    'middlename' : 'Mitt',
                    'lastname' : 'Romney',
                    'party' : 'R',
                    'twitter_id' : 'MittRomney',
                    'phone' : '857-288-3500'
                }            
            else:
                person = None

        if person is not None:
            cache.set(cache_key, person, MEMCACHED_TIMEOUT)

    return person

@app.route('/legislators/search')
def legislators_search():
    zipcode = request.args.get("zipcode", None)

    if zipcode:
        legislators = load_legislators(zipcode)
        title = "Legislators for " + zipcode
        return render_template('legislators.html', zipcode=zipcode, legislators=legislators, title=title)
    else:
        app.logger.warning("Could not load zipcode; retrying. Zipcode: " + str(request.args.get("zipcode", None)))
        title = "Legislators"
        return render_template('legislators_form.html', title=title)

@app.route('/legislators/')
def legislators():
    return redirect(url_for('legislators_search'))

def load_legislators(zipcode):

    #check the memcached cache first
    cache_key = "zipcode_" + zipcode
    legislators = cache.get(cache_key)
    breakcache = request.args.get("breakcache", None) 
    if legislators is None or breakcache is not None:
        legislators = sunlight.congress.legislators_for_zip(zipcode=zipcode)
        senators = []
        representatives = []
        for person in legislators:
            if person['chamber'] == 'senate':
                senators.append(person)
            elif person['chamber'] == 'house':
                representatives.append(person)
        if len(senators) == 0 and len(representatives) > 0:
            senators.append({
                "district": "Senior Seat", 
                "title": "Sen", 
                "in_office": True, 
                "state": "DC", 
                "crp_id": "0", 
                "chamber": "senate", 
                "party": "I", 
                "firstname": "Casper", 
                "middlename": "The Friendly", 
                "lastname": "Ghost", 
                "facebook_id": "pages/Casper-the-Friendly-Ghost/92386373162", 
                "gender": "M", 
                "twitter_id": "ThFriendlyGhost", 
            })
            senators.append({
                "district": "Junior Seat", 
                "title": "Sen", 
                "in_office": True, 
                "state": "DC", 
                "crp_id": "0", 
                "chamber": "senate", 
                "party": "I", 
                "firstname": "Baratunde", 
                "middlename": "", 
                "lastname": "Thurston", 
                "facebook_id": "baratunde", 
                "gender": "M", 
                "twitter_id": "baratunde", 
            })
        legislators = {'Senate' : senators, 'House' : representatives}
        if legislators is not None:
            cache.set(cache_key, legislators, MEMCACHED_TIMEOUT)
    # else:
        # print("LEGS FROM CACHE")
    return legislators

@app.route('/subscribe_sms', methods=['POST'])
def subscribe_sms():
    phone_number = request.form.get("subscribe_number", None)
    legislator_id = request.form.get("legislator_id", None)
    number = phonenumbers.parse(phone_number, 'US')
    number = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    app.logger.debug("Sending message to %s" % number)
    

    if phone_number and legislator_id:
        # SAVE PHONE NUMBER SOMEWHERES
        #TODO make sure the phone number format is correct; Twilio is picky about this.
        subscription = SMSSubscription(phone_number = number, legislator_id = legislator_id)
        subscription.save()
        #Send a confirmation message to that number
        call = client.sms.messages.create(to=phone_number,
                from_= app.config['TWILIO_OUTGOING'], 
                body="Thank you for subscribing to LFLN alerts! If you don't want to receive these anymore, reply STOP")
        #TODO implement 'reply STOP to stop!
        return render_template('subscribe_result.html', success=True)
    else:
        return render_template('subscribe_result.html', success=False)

def search(search_query, max_results=MAX_SEARCH_RESULTS):
   pass

if __name__ == '__main__':
    print("port: ", app.config['PORT'])
    app.run(host='0.0.0.0', port = app.config['PORT'], debug=app.config['APP_DEBUG'])
