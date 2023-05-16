# CS 152 - Trust and Safety Engineering
## Discord Bot Framework Code

This is the base framework for students to complete Milestone 2 of the CS 152 final project. Please follow the instructions you were provided to fork this repository into your own repository and make all of your additions there. 

Install libraries
```
python3 -m pip install requests
python3 -m pip install discord.py
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
2. Automatically detects offensive messages by using `profanity-check` library.
    - If score > 0.95, deletes the message directly (like "fuck you")
    - Else, if score > 0.4, forward the message to moderator (like "I hate you") with the following information:
      - Forwarded message:
      - \<user_name\>: \<message\>
      - Evaluated: \<score\>
3. 2 adversarial strategies: 
   - After message is edited, detects the offensive contents again. 
4. User reports go to mod channel with the following information:
   1. Reported message: \<user_name\>: \<message\>
   2. Report flow: A -> B -> C