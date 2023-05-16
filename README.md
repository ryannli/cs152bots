# CS 152 - Trust and Safety Engineering
## Discord Bot Framework Code

This is the base framework for students to complete Milestone 2 of the CS 152 final project. Please follow the instructions you were provided to fork this repository into your own repository and make all of your additions there. 

Install libraries
```
python3 -m pip install alt-profanity-check
python3 -m pip install scipy
```
If there are errors from scipy, try uninstall it first `python3 -m pip uninstall scipy` and then reinstall `python3 -m pip install scipy`. 

Run the Discord bot by
``` 
python3 bot.py
```

Current implementated functions:
1. Basic user reporting flow. Follow Milestone 2 guidelines to test on Discord. 
2. Automatically deletes offensive messages like "fuck you" by using `profanity-check` library.
3. After message is edited, detects the offensive contents again. 