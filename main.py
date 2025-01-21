
from pixie_sync import PixConnection
import aiohttp
import asyncio


import urllib.parse
from tqdm.asyncio import tqdm_asyncio
import re
import time

import sqlite3

MAIN_EMAIL = input('email = ? ')
MAIN_PASSWORD = input('password = ? ')



IS_PERFECTIONIST = True #if this is on, it will move onto the next topic when it doesn't know the answer to a question 



sql_connection = sqlite3.connect('answers_save.db')
cursor = sql_connection.cursor()

answer_cache = {}



#i doubt pix is gonna intentionally feed me an sql injection
def create_tables(competences):
    sql = 'CREATE TABLE IF NOT EXISTS {} (attributes TEXT PRIMARY KEY, answer TEXT)'
    for competence_id in competences:
        cursor.execute(sql.format(competence_id))
    
    sql_connection.commit()

def insert_into_cache(competence_id,attributes,answer):
    #we assume url-encoded stuff is sql-safe

    answer = answer.replace('"','""') #escaping the quotation marks
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