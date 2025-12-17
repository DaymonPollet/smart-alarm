- Connecting with the fitbit client:
(this might have been resolved on my own eventually but AI was way smarted in this aspect and I used Gemini because fitbit is a google related product). I did first try to let the ai do it and made sure to give mock values as private keys and such (because am sceptical about letting AI use the real data) but I also have a paid subscription so I think am save to provide such sensitive info. 

- Registering model on azure:
This was the most tricky part and I have to be honest here, I had to use a lot of AI because I was totally lost in the sauce while debugging both of these issues. I will not describe all the prompts and results because they are way to numerous and spend over different coding sessions. 
I will say that I DO NOT regret letting AI help me with this because if I didn't I think I would still have been trying to find how to register a model. I also had many bizare problems like kernel crashes, venv corruption and an internet outage and I was feeling the stress, so I helped myself. 

The prompts consisted out of me giving the errors and letting ai give me commands to try and fix the connection to azure. I eventually asked very specifically to generate and execute specific scripts to diagnose the issue. Scripts and code executed (as provided by the AI) include making a temp env in a seperate process to bypass the problem of the system python and my venv used not allowing me to install azure programs or login to azure. We found problems as my browser (google) expiring a key / token so if I opened the url in the google browser (which is configured for ehtical hacking purposes) it would make the token expire and I wouldn't be able to login anymore using that same url. Other problems where that my terminal would truncate output in an (almost unreadable and extremely verbose way). The best thing we got out of it was that I now know a good way of doing a healthcheck to a model in the cloud is to provide it an example record and see if it returns the probability distribution.

- Frontend building: 

I simple give the AI a list of all the backend endpoints we had and asked to make a simple frontend using prompt: Here are the api andpoints we have, with respect to what the endpoints take as arguments and output back as data, make a simple frontend for the user to interact with these endpoints: (here would be any version of the app.py used at the time (quite a couple of versions))

(This prompt was used a couple of times because endpoints were later added aswell.)

- Frontend refactoring:

The frontend got to massive after a while and was handling almost everything we did.
I give AI the file and said "this frontend is to massive, refactor it and give me logical pieces of code accurding to there functionality. Your first job is to create service/api.js moving all the axios logic out making it easier to test and debug the code (which is still a mess). Try to keep these princibles in mind SoC, modularity, scalabity and readibility / maintainablity. Here is the code: (i will not paste + 600 lines of code here) the file was App.js at commit a7fcbfd3a1a9305abbb12c2ae02c30f6fb1fa088

I then asked the same for the css (which was over over 600 lines)

This took the AI massive time and a couple times of trying (but the idea was that i would later be able to modularly implement my own css (I have a cool idea and style I want to use if I still have time))

After the refactoring our structure looked like this (we already had a very small index js and css but the only other frontend files where the app.js and css so this is a very nice improvement): frontend/src/
├── services/
│   └── api.js                    # All HTTP/API calls
├── hooks/
│   ├── index.js                  # Hooks export
│   ├── useSleepData.js           # Sleep data fetching hook
│   └── useConfig.js              # Config state hook
├── components/
│   ├── index.js                  # Components export
│   ├── AlarmPopup/               # Alarm notification
│   ├── ArchitectureInfo/         # System docs
│   ├── Card/                     # Reusable card
│   ├── DeepSleepChart/           # Bar chart
│   ├── ProbabilityBars/          # ML probabilities
│   ├── QualityBadge/             # Quality indicator
│   ├── SleepChart/               # Line chart
│   ├── SleepHistory/             # History table
│   └── StatusBadge/              # Status indicator
├── utils/
│   └── helpers.js                # Utility functions
├── App.js                        # Main component (~400→ cleaner)
└── App.css                       # CSS with variables



I later did it again and got: backend/local-api/
├── app.py              # Main entry (120 lines)
├── app.old.py          # Backup
└── routes/
    ├── __init__.py     # Blueprint registration + background fetch
    ├── auth_routes.py  # OAuth handling
    ├── alarm_routes.py # Alarm management
    └── sleep_routes.py # Data fetching & predictions

frontend/src/
├── App.js                          # UI only (210 lines)
├── App.old.js                      # Backup
└── hooks/
    └── useSleepDashboard.js        # All state & handlers (260 lines)


- Fix a commit + stuck in vim:

prompt: "i am stuck here: Improved functionality by:                                                         - Added an alarm service with a default timewindow of 30 (will not yet play alarm sound

Created custom hooks (useConfig, useSleepData) for better state management

- Added Azure Insights service for cloud monitoring

- Cleaned up App.js and moved logic to services/api.js".git/COMMIT_EDITMSG[+] [unix] (15:12 16/12/2025)                            1,1 Top // how can i quite first, then open it in something else then vim

"

response: esc + :q!
git config --global core.editor "notepad"
git config --global core.editor "code --wait"
git commit --amend
git commit --amend --no-edit


- Verbose azure output

I tried to connect to the azure oit hub service but they outputs where all massive logs of connectiondropouterrors which was very bizarre. I simply asked ai to 'fix this' and give the file in question 'iothub_service.py' and it provided me with a bunch of bizare expectionhandling but this worked and I can now sync my iot status back and forward.



- Debugging github runner going offline:

My prompt was: 
now what: admin@raspberrypi-daymon:~ $ sudo nmcli networking off
sudo nmcli networking on
admin@raspberrypi-daymon:~ $ ping -c 3 8.8.8.8
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
--- 8.8.8.8 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 2056ms
admin@raspberrypi-daymon:~ $ ^C
admin@raspberrypi-daymon:~ $ ip route
default via 192.168.137.1 dev eth0 proto static metric 100
default via 192.168.0.1 dev wlan0 proto dhcp src 192.168.0.207 metric 600
192.168.0.0/24 dev wlan0 proto kernel scope link src 192.168.0.207 metric 600
192.168.137.0/24 dev eth0 proto kernel scope link src 192.168.137.11 metric 100
admin@raspberrypi-daymon:~ $

Here was the response:

Here is exactly what's happening: Your Pi has two front doors, and it’s trying to walk through the broken one.

Looking at your ip route, you have two "default" routes. In Linux, the route with the lowest metric wins.

eth0: Metric 100 (via 192.168.137.1). This is usually the default IP when a Windows PC shares its internet via a cable. This path is currently dead/unreachable.

wlan0: Metric 600 (via 192.168.0.1). This is your actual WiFi router. This path works, but the Pi is ignoring it because 600 is "more expensive" than 100.

The Fix: Force the WiFi to be the Priority
We need to tell the Pi that the WiFi (wlan0) is actually the preferred route to the internet.

1. Delete the "Fake" route temporarily: Run this to immediately kill the broken path and let the WiFi take over:

Bash

sudo ip route del default dev eth0
Now try ping -c 3 8.8.8.8 again. It should work immediately.

2. Make it permanent (using nmcli): If you don't do this, the broken route will come back next time you reboot or plug in a cable. We will set the Ethernet metric to be much higher (less preferred) than the WiFi.

Bash

# Find the name of your ethernet connection (it's usually "Wired connection 1")
nmcli connection show

# Set its metric to 2000 (very low priority)
# Replace "Wired connection 1" with the name from the previous command if it's different
sudo nmcli connection modify "Wired connection 1" ipv4.route-metric 2000

# Restart the connection to apply
sudo nmcli connection up "Wired connection 1"





Dubbuging info: On your laptop browser, go to: http://192.168.0.207:30080/api/auth/code (your Pi's address)

This shows a form. First, you need to start the OAuth flow:

Go to http://192.168.0.207:30080/api/auth/login to get the auth URL
Or manually go to: https://www.fitbit.com/oauth2/authorize?client_id=23TMGB&response_type=code&scope=heartrate+activity+sleep+profile&redirect_uri=http://127.0.0.1:8080
Authorize on Fitbit - it will redirect to http://127.0.0.1:8080/?code=XXXXX... which fails (connection refused)

Copy the code from that failed URL (everything after code= and before #)

Go back to http://192.168.0.207:30080/api/auth/code and paste the code

Submit - the Pi will exchange the code for tokens and store them