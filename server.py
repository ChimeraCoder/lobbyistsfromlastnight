#! /usr/bin/env python

from __future__ import division, print_function
from flask import Flask
from flask import request, redirect, url_for
from flask import Response
from flask import render_template
from flask import jsonify
from functools import wraps
import os
import sys


app = Flask(__name__)
app.config.from_envvar('APP_SETTINGS')

#TODO remove this!
app.debug = True

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

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/', )
@requires_auth
def authorize():
    return "This is just a stub"



def search(search_query, max_results=MAX_SEARCH_RESULTS):
   pass

if __name__ == '__main__':
    app.run()
