Lobbyists From Last Night
========================

It's 10 p.m. Do you know where your lawmakers are?
------------------------

Lobbyists From Last Night is a project made during the [Comedy Hack Day](http://comedyhackday.org/) in NYC. 

We’re tired of missing out on the pheasant hunts, BBQs and yacht parties that accompany a fat campaign contribution. We want pics, we want stories and we want answers.


Made using the Sunlight Congress API and Political Party Time.


### Contributing

#### Configuration
A number of configuration variables need to be defined, such as Twilio/Sunlight API keys and database credentials. These will be referenced from environment variables. You can easily check if you are missing any variables by typing `make`. If `make` exits without any output, you're good to go! 

````
lobbyistsfromlastnight$ make
lobbyistsfromlastnight$ 
````
Otherwise, it will tell you the first variable you are missing.

````
lobbyistsfromlastnight$ make
Environment variable APP_SETTINGS not set
make: *** [guard-APP_SETTINGS] Error 1
lobbyistsfromlastnight$ export APP_SETTINGS=settings.py
lobbyistsfromlastnight$ #Now, running make again will either succeed or tell you the next variable missing.
````

A full list of all environment variables needed can be seen in the Makefile, under the `check-envs` target.
