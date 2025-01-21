#use this when aiohttp goes down


from pixie_sync import PixConnection
import aiohttp
import asyncio


import urllib.parse
from tqdm.asyncio import tqdm_asyncio
import re
import time

import sqlite3

#aiohttp: SPEEEEDDDDDDDDDDD (until you get detected lol)

#perfectionist testaccount: 522 pix
# MAIN_EMAIL = 'perfectstudent@perfectionuniversity.edu'
# MAIN_PASSWORD = 'iAmSoPerfect11'

#non_perfectionist testaccount: 768 pix
# MAIN_EMAIL = 'notperfectstudent@normaluniversity.edu'
# MAIN_PASSWORD = 'iAmSoCool11'

#perfectionist testaccount with cache: 10 pix (LOLLLL)
MAIN_EMAIL = input('email = ? ')
MAIN_PASSWORD = input('password = ? ')



IS_PERFECTIONIST = True #if this is on, it will move onto the next topic when it doesn't know the answer to a question 



# CACHE PLAN:
#FOR EVERY CATEGORY, CREATE A TABLE [competenceid], use attributes_parsed as the key.
#GRAB STUFF FROM THE CATEGORY INSTEAD OF RELYING ON BACKUP ACCOUNTS

sql_connection = sqlite3.connect('answers_save.db')
cursor = sql_connection.cursor()

answer_cache = {}

# async_cap = asyncio.Semaphore(100)

#i doubt pix is gonna intentionally feed me an sql injection
def create_tables(competences):
    sql = 'CREATE TABLE IF NOT EXISTS {} (attributes TEXT PRIMARY KEY, answer TEXT)'
    for competence_id in competences:
        cursor.execute(sql.format(competence_id))
    
    sql_connection.commit()

def insert_into_cache(competence_id,attributes,answer):
    #we assume url-encoded stuff is sql-safe

    answer = answer.replace('"','""') #escaping the quotation marks
    # print(f'INSERT INTO {competence_id} VALUES ( "{attributes}", "{answer}"  )')
    cursor.execute(f'INSERT OR IGNORE INTO {competence_id} VALUES ( "{attributes}", "{answer}"  )')

def get_from_cache(competence_id,attributes):
    sql = cursor.execute(f'SELECT answer FROM {competence_id} WHERE attributes = "{attributes}" ' )
    return sql.fetchone()




def parse_qrocm(input_text):
    output = ''
    already_selected = False
    for line in input_text.splitlines():
        if len(line) == 0:
            continue

        if line[0] == '-':
            if not already_selected:
                already_selected = True
                output += line + '\n'
        else:
            already_selected = False
            output += line + '\n'

    return output[:-1]



# aync_cap = asyncio.Semaphore(50)



def load_saved_accounts():
    connections = []
    with open('account_cache.mrrp') as file:
        for line in file:
            strip = line.strip()
            connections.append(PixConnection(auth_token=strip))
    return connections


def write_accounts(connection_list):
    for connection in connection_list:
        with open("account_cache.mrrp", "a") as myfile:
            myfile.write(connection.auth_token + '\n')

async def generate_accounts(amount_to_generate):
    tasks = []
    connections = []
    async with aiohttp.ClientSession() as session:
        for _ in range(amount_to_generate):
            new_conn = PixConnection(session)
            tasks.append(new_conn.signup_random_account())
            connections.append(new_conn) 
        await tqdm_asyncio.gather(*tasks)
    return connections




        
        

        
        


def main():




    main_conn = PixConnection()
    main_conn.login(MAIN_EMAIL,MAIN_PASSWORD)
    # main_conn.signup_random_account()
    
    main_competences = main_conn.get_competences() #these don't change relative to accounts so we only have to get them once

    create_tables(main_competences)    
    

    for competence_id in main_competences:

            main_assessment_id = main_conn.start_or_resume(competence_id)



            main_challenge_id = True

            completed = True

            while main_challenge_id:
                main_challenge_id, challenge_attributes = main_conn.get_current_challenge(main_assessment_id)

                if not main_challenge_id:
                    print('assessment complete...\n\n')
                    break
        
                attributes_parsed = urllib.parse.urlencode(challenge_attributes)


                correct_answer = '#ABAND#'
                    
                sql_response = get_from_cache(competence_id,attributes_parsed)
                if sql_response:
                    correct_answer = sql_response[0]

                else:
                    print('no answer found :c')
                    if IS_PERFECTIONIST:
                        print('SKIPPING:\n\n')
                        completed = False
                        break

                _, is_correct = main_conn.answer_question(main_challenge_id,main_assessment_id,correct_answer)
                if not is_correct:
                    print('put an answer in, but its wrong???')
                    print(correct_answer)
                    print(challenge_attributes)
                else:
                    print('put a CORRECT answer in!!!')
            
            if completed:
                main_conn.complete_assessment(main_assessment_id)
    sql_connection.close()           





main()