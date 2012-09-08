from os import environ

MONGOALCHEMY_DATABASE = environ.get('MONGODB_DATABASE')
MONGOALCHEMY_SERVER = environ.get('MONGODB_HOST')
MONGOALCHEMY_PORT = environ.get('MONGODB_PORT')
MONGOALCHEMY_USER = environ.get('MONGODB_USER')
MONGOALCHEMY_PASSWORD = environ.get('MONGODB_PASSWORD')
MONGOALCHEMY_SERVER_AUTH = False

DEBUG = True
APPLICATION_ROOT = environ.get('APPLICATION_ROOT')

