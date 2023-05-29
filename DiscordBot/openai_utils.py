import os
import openai
import json
from collections import OrderedDict

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    openai.api_key = tokens['openai']

def convert_string_to_dict(message):
    result = OrderedDict()
    try:
        for item in message.split('\n'):
            item = item.split(':')
            if len(item) == 2:
                item_type = item[0].strip()
                item_score = item[1].split('(')[0].strip()
                result[item_type] = int(item_score)
    except (ValueError, IndexError):
        # Handle any exceptions that may occur during conversion
        print(f"Error converting message: {message}. Skipping")
    return result

def get_openai_dict_scores(text):
    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
    {"role": "system", "content": '''You are a content moderation system. 

    Please help to classify if the following text from a web user is any of the following categories. For each category, reply one of 1, 2, 3, 4, 5. 1 means negligible (like "I love you", "it's a cloudy day"). 5 means very severe (like "fuck you", "vegans are super stupid"). 
    Your reply should use the following format and contains all the following categories:

    Scam: {SCORE}
    Offensive Content: {SCORE}
    Harrassment and bullying: {SCORE}
    Harrassment and unwanted sexual content: {SCORE}
    Harrassment and leaking private Information: {SCORE}
    Harrassment and hate speech: {SCORE}
    Danger: {SCORE}
    Illegally published content: {SCORE}
    Misinformation: {SCORE}
    '''},

    {"role": "user", "content": text},
    ]
    )
    message = response['choices'][0]['message']['content']
    print("OpenAI response message debug info: ")
    print(message)
    return convert_string_to_dict(message)
