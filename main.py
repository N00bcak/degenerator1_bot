import telebot
import os
from nltk.corpus import words, wordnet, brown
import random
import string
import json
import logging
import sys

# Opens debugging mode
# Used nowhere but good for debugging telebot requests
logging.basicConfig(level=logging.DEBUG if '-log' in sys.argv else logging.INFO)

# Alternatively you can also write the logs into a file like so:
# sys.stdout=open('log.txt','w')

# Get your own api key >:(
f=open('api_key.txt','r')
API_KEY=f.read()
bot=telebot.TeleBot(API_KEY)

# Helper functions
def find_letter(word,letter):
    # Returns the positions in the word where the letter can be found
    return [i for i in range(len(letter)) if word==letter[i]]

def initialize_freq_list(freq_list):
    for i in string.ascii_lowercase:
        freq_list[i]=0

# Again debug is not used but good for debugging nonetheless :)
def log_to_console(message,level):
    if level=='info':
        logging.info('\033[0;34m'+message+'\033[0m')
    elif level=='debug':
        logging.debug('\033[0;32m'+message+'\033[0m')


#Initialization of the word list
wordlist=[]
weightlist=[]
for i in words.words()+list(wordnet.words())+list(brown.words()):
    if 5<=len(i)<=12:
        wordlist.append(i.lower())
        weightlist.append(1/(len(i)**2))

# We will store the data from each user's interactions with the bot as a nested dict.
# It doesn't make much sense to write this data into a json file so I shall not.
words={}
word_letter_freqs={}
guess_counts={}
guess_logs={}
letter_freqs={}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,'Welcome! I am a lame bot that offers a lame word guessing game. Give it a go with "/wordgame" or I will be sad.' +b'\xF0\x9F\xA5\xBA'.decode('utf-8')+'\n\nTo guess a word, please **reply** to each of my messages!')


@bot.message_handler(commands=['wordgame'])
def word_game(message):
    
    # Tries to start a game for the user unless they already have one running.

    global words
    sender=message.from_user.username
    log_to_console(f"{sender} has called the word_game function",'info')

    if sender in words.keys() and len(words[sender])>0:
        bot.reply_to(message,'Game is already running!')
        log_to_console(f"But {sender} already has a game!",'info')
    else:
        '''
        A word is randomly generated for each user that requests a game.
        Roughly speaking longer words appear with a lower probability.
        We keep a frequency list to facilitate later gameplay.
        '''
        guess_counts[sender]=0
        guess_logs[sender]=''
        words[sender]=random.choices(wordlist,weights=weightlist)[0]

        if sender not in word_letter_freqs.keys():
            word_letter_freqs[sender]={}
        initialize_freq_list(word_letter_freqs[sender])
        for i in words[sender]:
            word_letter_freqs[sender][i]+=1
        
        bot.reply_to(message,f"Word Game started! Please guess a {len(words[sender])} letter word!")
        log_to_console(f"{sender} sent the message and the word is {words[sender]}.",'info')

@bot.message_handler(func=lambda x:True, content_types=['text'])
def guess(message):

    ''' 
    Retrieves the user's guess and compares it to the word that was generated for them.
    Because I'm bored we are also checking that the guess:
    1) Is lower case alphabetic
    2) Is a word
    3) Is of the appropriate length
    4) Was not already attempted before by the user.
    '''
    global guess_counts, guess_logs, words, word_letter_freqs,letter_freqs


    if message.reply_to_message is None or message.reply_to_message.from_user.username!=bot.get_me().username:
        return None
    
    sender=message.from_user.username
    log_to_console(f"{sender} has called the guess function",'info')

    txt=message.text.lower()

    if sender not in words.keys() or words[sender]=='':
        bot.reply_to(message, "You haven't started a game, or your game has expired! Please start a new game by using the command /wordgame!")
    elif not set(txt).issubset(set(string.ascii_lowercase)):
        bot.reply_to(message,"Please give me a word, not a malicious payload!")
    elif txt not in wordlist:
        bot.reply_to(message, "Please give me a VALID word (NLTK, WordNet, Brown corpus).")
    elif len(txt)!=len(words[sender]):
        bot.reply_to(message,f"The word is {len(words[sender])} letters long, not {len(txt)} letters long!")
    elif txt in guess_logs[sender]:
        bot.reply_to(message,"You've already guessed this word!")
    else:
        '''
        Briefly,
        If the letter is not in the word, return the black square.
        If the letter is in the word but at the wrong position, return the yellow square.
        Else return the green square.
        We will use a dictionary to account for duplicate letters.
        '''  
        log_to_console(f"{sender} has guessed {txt}",'info')
        guess_counts[sender]+=1
        guess_response=''
        letter_freqs[sender]={}

        '''
        We track whether the guess exactly matches the word.
        Obviously everything must be in place so as long as the positioning is wrong or a letter is missing the word is incorrect.
        '''

        correct=True
        initialize_freq_list(letter_freqs[sender])

        unmatched_indices=[]
        for i in range(len(txt)):
            if txt[i]==words[sender][i]:
                letter_freqs[sender][txt[i]]+=1
                guess_response+=b'\xf0\x9f\x9f\xa9'.decode('utf-8') # Green Square
            else:
                unmatched_indices.append(i)
        
        if len(unmatched_indices)>0:
            correct=False
             
        for i in unmatched_indices:
            positions=find_letter(txt[i],words[sender])
            letter_freqs[sender][txt[i]]+=1
            if len(positions)==0 or letter_freqs[sender][txt[i]]>word_letter_freqs[sender][txt[i]]:
                guess_response=guess_response[:i]+b'\xe2\xac\x9b'.decode('utf-8')+guess_response[i:] # Black Square
            else:                
                guess_response=guess_response[:i]+b'\xf0\x9f\x9f\xa8'.decode('utf-8')+guess_response[i:] # Yellow Square
        guess_logs[sender]+=guess_response+'\n'+txt+'\n'

        # Now that we finished handling the guesses, let's show the user if they were correct or not.
        if correct==True:
            bot.reply_to(message,f"Attempt {guess_counts[sender]}\n\n{guess_logs[sender]}\nCongratulations, you got the word!")
            
            log_to_console(f"{sender} managed to guess the word {txt} in {guess_counts[sender]} tries.",'info')
            # Ends the game and cleans up for the current user.
            words[sender]=''
            initialize_freq_list(word_letter_freqs[sender])
            guess_counts[sender]=0
            guess_logs[sender]=''

        else:
            bot.reply_to(message,f"Attempt {guess_counts[sender]}\n\n{guess_logs[sender]}\nNope, keep guessing!")
        
bot.infinity_polling()
