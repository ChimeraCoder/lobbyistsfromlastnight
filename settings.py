from os import environ

MONGOALCHEMY_DATABASE = environ.get('MONGODB_DATABASE')
MONGOALCHEMY_SERVER = environ.get('MONGODB_HOST')
MONGOALCHEMY_PORT = environ.get('MONGODB_PORT')
MONGOALCHEMY_USER = environ.get('MONGODB_USER')
MONGOALCHEMY_PASSWORD = environ.get('MONGODB_PASSWORD')
MONGOALCHEMY_SERVER_AUTH = False


MEMCACHED_HOST = environ.get('MEMCACHED_HOST')
MEMCACHED_PORT = environ.get('MEMCACHED_PORT')

DEBUG = environ.get("APP_DEBUG", False)

APPLICATION_ROOT = environ.get('APPLICATION_ROOT')

