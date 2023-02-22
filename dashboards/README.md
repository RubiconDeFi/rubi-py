# MORE COMING SOON

### just some helpful setup notes
if you are having trouble getting the most recent rubi version, you may need to run `poetry cache clear pypi --all` and then try to run `poetry lock --no-update` followed by `poetry install` xD

### redis
in order to support web hosting of dash applications, we take advantage of redis and worker applications to obfuscate the data processing from the application itself. to run these apps locally, 
there are a couple of additional steps that you will need to take. this current setup is with macOS in mind, and i hope to soon add non-mac instructions. this setup was designed for heroku 
hosting, and there are several things that we should be striving to do going forward that will be outlined below. 

to install redis: `brew install redis`
set up a redis server (in a seperate terminal): `redis-server`
now you can run the worker application: 