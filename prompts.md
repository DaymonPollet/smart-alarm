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