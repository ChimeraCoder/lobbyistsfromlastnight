#! /usr/bin/env sh

mongo $MONGODB_HOST:$MONGODB_PORT/$MONGODB_DATABASE -u $MONGODB_USER -p $MONGODB_PASSWORD
