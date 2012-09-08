#! /bin/sh

#Url should be specified as the first argument and formatted as
#mongodb://user:password@hostsubdomain.hostdomain.hosttld:port/database


MONGO_VARS=$(python -c "import re; splt = list(re.split('\W', '$1')); print('\n'.join((splt[3], splt[4], '.'.join(splt[5:-2]), splt[-2], splt[-1])))")

echo "export MONGODB_URI=$1"

y=0
VARNAMES=("MONGODB_USER" "MONGODB_PASSWORD" "MONGODB_HOST" "MONGODB_PORT" "MONGODB_DATABASE")
for var in $MONGO_VARS
do
    echo "export" "${VARNAMES[$y]}="$var
    eval "export" "${VARNAMES[$y]}="$var
    y=$[$y+1]
done


