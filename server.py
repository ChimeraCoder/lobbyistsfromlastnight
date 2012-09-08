#! /usr/bin/env python

from __future__ import division, print_function
from flask import Flask
from flask import request, redirect, url_for
from flask import Response
from flask import render_template
from flask import jsonify
from functools import wraps
from flask.ext.login import LoginManager, current_user, login_required, login_user, logout_user, UserMixin, AnonymousUser
import os
import sys


app = Flask(__name__)
app.config.from_envvar('APP_SETTINGS')
app.secret_key = os.getenv("SESSION_SECRET")


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

from flaskext.mongoalchemy import MongoAlchemy, BaseQuery
db = MongoAlchemy(app)



#TODO remove this!
app.debug = True
login_manager = LoginManager()
login_manager.setup_app(app)

MAX_SEARCH_RESULTS = 20


def check_auth(username, password):
    #TODO implement proper auth
    return True


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
            'Could not verify your access level for that URL.\n'
            'You have to login with proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'})

    
@app.route('/')
def welcome():
    return "Hello, world"

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
        cache.set(userid, rv, MEMCACHED_TIMEOUT)
    return rv

@app.route('/login/', methods = ["GET", "POST"])
def login():
    form = LoginForm()
    print("testing form", request.method)
    if form.validate_on_submit():
        #login and validate user
        print("logging in user?")
        login_user(form.user)
        flash("Logged in successfully")
        return redirect(request.args.get("next") or url_for("welcome"))
    else:
        print(form)
        print(form.__dict__)

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
        accept_tos = request.form['accept_tos']
        new_user = MongoUser(username = username, password = bcrypt.hashpw(password, bcrypt.gensalt()), email = email, created_at = int(time.time()))
        new_user.save()
        return redirect(url_for('welcome'))
    else:
        return render_template("signup.html", form=form)


@login_manager.unauthorized_handler
def unauthorized():
    return render_template("index.html", flash="unauthorized", intro_text="You need to log in to view this page")

       
@app.context_processor
def inject_user_authenticated():
    return dict(user_authenticated = current_user.is_authenticated())
    

@app.route('/', )
def authorize():
    return "This is just a stub"



def search(search_query, max_results=MAX_SEARCH_RESULTS):
   pass

if __name__ == '__main__':
    app.run()
