# CS 152 - Trust and Safety Engineering
## Discord Bot Framework Code

This is the base framework for students to complete Milestone 2 of the CS 152 final project. Please follow the instructions you were provided to fork this repository into your own repository and make all of your additions there. 

Install libraries
```
python3 -m pip install requests
python3 -m pip install discord.py
python3 -m pip install alt-profanity-check
python3 -m pip install scipy
python3 -m pip install editdistance
python3 -m pip install openai
python3 -m pip install argparse
```
If there are errors from scipy, try uninstall it first `python3 -m pip uninstall scipy` and then reinstall `python3 -m pip install scipy`. 

Run the Discord bot by
``` 
python3 bot.py
```

Run the Discord bot with OpenAI detection
```
python3 bot.py --openai=true
```

Example for using formatter library:
```
>>> import formatter
>>> dict = {'A': 5, 'B': "3", 'C': "DD"}
>>> str = formatter.format_dict_to_str(dict)
>>> str
'`A`: 5\n`B`: 3\n`C`: DD\n'
>>> formatter.unformat_str_to_dict(str)
OrderedDict([('A', '5'), ('B', '3'), ('C', 'DD')])
```
Current implementated functions:
1. Basic user reporting flow. Follow Milestone 2 guidelines to test on Discord. 
2. Automatically detects offensive messages by using `profanity-check` library.
    - If score > 0.95, deletes the message directly (like "fuck you")
    - Else, if score > 0.4, forward the message to moderator (like "I hate you"). Example message: 
      - `reporter`: SYSTEM AUTOMATIC
      - `author`: My Name
      - `message`: i'll kill you
      - `link`: https://discord.com/channels/1103033282779676743/1103033284834902076/1108947923355574352
      - `metadata`: profanity_check score is 0.83
3. Automatically detects offensive messages by using OpenAI. Detect for 9 different abusive categories and rate in scale 1-5 (from negligible to severe)
    - If at least 2 categories has score>=4, deletes the message directly (like "fuck you")
    - Else, if at least 1 category has score>=3, forward the message to moderator (like "I hate you"). Example message: 
      - `reporter`: SYSTEM AUTOMATIC
      - `author`: My Name
      - `message`: i'll kill you
      - `link`: https://discord.com/channels/1103033282779676743/1103033284834902076/1108947923355574352
      - `metadata`: OpenAI detected harmful score (scale 1-5) is ...
4. 2 adversarial strategies: 
   - After message is edited, detects the offensive contents again. 
5. User reports go to mod channel. Example message:
      - `reporter`: 81149813901741260812
      - `author`: My Name
      - `message`: i'll kill you
      - `link`: https://discord.com/channels/1103033282779676743/1103033284834902076/1108947923355574352
      - `metadata`: profanity_check score is 0.83