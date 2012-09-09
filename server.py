#! /usr/bin/env python

from __future__ import division, print_function
from flask import Flask
from flask import request, redirect, url_for
from flask import Response
from flask import render_template
from flask import flash
from flask import jsonify
from functools import wraps
from flask.ext.login import LoginManager, current_user, login_required, login_user, logout_user, UserMixin, AnonymousUser
import os
import sys
import sunlight
import json
import bcrypt
import time
import urllib2
import csv
import re

app = Flask(__name__)
app.config.from_envvar('APP_SETTINGS')
app.secret_key = os.getenv("SESSION_SECRET")

from werkzeug.contrib.cache import MemcachedCache
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

cache = MemcachedCache([app.config['MEMCACHED_HOST'] + ":" + app.config['MEMCACHED_PORT']])

from flaskext.mongoalchemy import MongoAlchemy, BaseQuery
db = MongoAlchemy(app)

MEMCACHED_TIMEOUT = 10 * 60
MEMCACHED_TIMEOUT_SUNLIGHT = 24 * 60 * 60

#TODO remove this!
app.debug = True
login_manager = LoginManager()
login_manager.setup_app(app)

MAX_SEARCH_RESULTS = 20

ROMNEY_CID = 'N00000286'
OBAMA_CID = 'N00009638'

sunlight.config.API_KEY = "5448bd94e5da4e4d8ca0052e16cd77e0"

    
@app.route('/')
def welcome():
    return render_template("home.html")
    # return "Hello, world"

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

    title = person['firstname'] + ' ' + person['lastname'] + ' | Events'
    return render_template('events.html', events=events, person=person, event_count=event_count, event_id=eid, title=title)

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
    for e in events:
	e['start_date'] = time.strptime(e['start_date'], "%Y-%m-%d")
    events.sort(key=lambda e: e['start_date'].tm_year)
    for e in events:
	e['start_date'] = time.strftime("%b %d, %Y", e['start_date'])
    events.reverse()

    return events   

def parse_tweet(tweet, event, person):
    tweet.replace("@lawmaker",  "@"+person['twitter_id'])

    contribution_regex = re.compile("\$[\d,]+")
    if event['contributions_info']:
        contribution_matches = contribution_regex.match(event['contributions_info'])
        if contribution_matches:
            contribution_amount = contribution_matches.group()
            tweet.replace("[Contributions Info]", contribution_amount)

    tweet.replace("[venue]", "venue")
    tweet.replace("[start time]", "start_time")
    if event.has_key("end_time"):
        tweet.replace("[end time]", "end_time")
    tweet.replace("[event date]", "start_date")
    tweet = tweet + " #lfln"

    if "[" in tweet:
        return None
    return tweet

def suggested_tweets(legislator, event):
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
        elif keyword == 'generic':
            for tweet in row[1:]:
                suggested_tweets.append(parse_tweet(tweet, event, legislator))

    def nonNone(x):
        if x: return 1
        else: return 0

    suggested_tweets = filter(nonNone, suggested_tweets)
    return suggested_tweets
        

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
                    'twitter_id' : 'BarackObama'
                }
            elif cid == ROMNEY_CID:
                person = {
                    'title' : 'Governor',
                    'firstname' : 'Willard',
                    'middlename' : 'Mitt',
                    'lastname' : 'Romney',
                    'party' : 'R',
                    'twitter_id' : 'MittRomney'
                }            
            else:
                person = None

        if person is not None:
            cache.set(cache_key, person, MEMCACHED_TIMEOUT)

    return person

@app.route('/legislators/search')
def legislators_search():
    zipcode = request.args.get("zipcode", None)
    if not zipcode:
        if current_user.is_authenticated() and not current_user.is_anonymous():
            user = load_user_by_username(current_user.username)
            if user.zipcode and len(user.zipcode) > 4:
                zipcode = user.zipcode


    if zipcode:
        legislators = load_legislators(zipcode)
        title = "Legislators for " + zipcode
        return render_template('legislators.html', zipcode=zipcode, legislators=legislators, title=title)
    else:
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



def search(search_query, max_results=MAX_SEARCH_RESULTS):
   pass

if __name__ == '__main__':
    app.run(host='0.0.0.0')
