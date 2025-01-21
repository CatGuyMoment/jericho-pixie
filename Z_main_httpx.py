from pixie_httpx import PixConnection
import aiohttp
import asyncio
import httpx

import urllib.parse
from tqdm.asyncio import tqdm_asyncio
import re
import time

import sqlite3

import ssl
#httpx version w/ ssl verifier context: hopefully a decent competitor for aiohttp?

#perfectionist testaccount: 522 pix
# MAIN_EMAIL = 'perfectstudent@perfectionuniversity.edu'
# MAIN_PASSWORD = 'iAmSoPerfect11'

#non_perfectionist testaccount: 768 pix
# MAIN_EMAIL = 'notperfectstudent@normaluniversity.edu'
# MAIN_PASSWORD = 'iAmSoCool11'

#perfectionist testaccount with cache: 10 pix (LOLLLL)
MAIN_EMAIL = 'mrs.memory@memorisationinstitute.edu'
MAIN_PASSWORD = 'MeWhen1Memorize'


IS_PERFECTIONIST = True #if this is on, it will move onto the next topic when it doesn't know the answer to a question 
BACKUP_ACCOUNTS = 50



# CACHE PLAN:
#FOR EVERY CATEGORY, CREATE A TABLE [competenceid], use attributes_parsed as the key.
#GRAB STUFF FROM THE CATEGORY INSTEAD OF RELYING ON BACKUP ACCOUNTS

sql_connection = sqlite3.connect('answers_save.db')
cursor = sql_connection.cursor()

answer_cache = {}
context = ssl.create_default_context()

timeout = httpx.Timeout(connect=None, read=None, write=None, pool = None)



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
    # async with aiohttp.ClientSession() as session:
    async with httpx.AsyncClient(timeout=None,verify=context) as session:
        for _ in range(amount_to_generate):
            new_conn = PixConnection(session)
            tasks.append(new_conn.signup_random_account())
            connections.append(new_conn) 
        await tqdm_asyncio.gather(*tasks)
    return connections



async def farm(connection,async_cap,session,competence_id):
    async with async_cap:
        connection.change_session(session)
        assessment_id = await connection.start_or_resume(competence_id)

        challenge_id = True
        while challenge_id:
            challenge_id, challenge_attributes = await connection.get_current_challenge(assessment_id)

            if not challenge_id:
                break
                
            attributes_parsed = urllib.parse.urlencode(challenge_attributes) #this will serve as our "question identifier". same question = same key = same answer.

            answer_guess = 'lalalalala'

            if challenge_attributes['type'] == 'QROCM-ind':
                answer_guess = '#ABAND#' #only skipping because it literally won't let me put gibberish in as the answer :sob: 

            if answer_cache[competence_id].get(attributes_parsed):
                answer_guess = answer_cache[competence_id][attributes_parsed]
            else:
                sql_response = get_from_cache(competence_id,attributes_parsed)
                if sql_response:
                    answer_guess = sql_response[0]
                    answer_cache[competence_id][attributes_parsed]  = answer_guess

            answer_id, is_correct = await connection.answer_question(challenge_id,assessment_id,answer_guess)

            if is_correct:
                # print('one of the scrapers got the right answer lol')
                continue

            correct_answers = await connection.get_correction(answer_id)
        
        
            if correct_answers: #this should usually always be true
                if 'QROCM' in challenge_attributes['type']:
                    correct_answers = parse_qrocm(correct_answers)
                else:
                     correct_answers = correct_answers.split('\n')[0]
                
                answer_cache[competence_id][attributes_parsed]  = correct_answers
                insert_into_cache(competence_id,attributes_parsed,correct_answers)


        
        

        
        


async def main():



    main_conn = None
    main_competences = None
   
    # async with aiohttp.ClientSession() as session:
    async with httpx.AsyncClient(timeout=timeout,verify=context) as session:
        main_conn = PixConnection(session)


        # await main_conn.login(MAIN_EMAIL,MAIN_PASSWORD)
        await main_conn.signup_random_account()
        main_competences = await main_conn.get_competences() #these don't change relative to accounts so we only have to get them once

    create_tables(main_competences)    
    
    random_conns = await generate_accounts(BACKUP_ACCOUNTS)
    # random_conns = load_saved_accounts()
    # write_accounts(random_conns)

    # async with aiohttp.ClientSession() as session:
    async with httpx.AsyncClient(timeout=timeout,verify=context) as session:
        
        main_conn.change_session(session)

        for competence_id in main_competences:

            main_assessment_id = await main_conn.start_or_resume(competence_id)

            tasks = []
            answer_cache[competence_id] = {}
            async_cap = asyncio.Semaphore(15)


            for connection in random_conns:
                tasks.append(farm(connection,async_cap,session,competence_id))

            await tqdm_asyncio.gather(*tasks)
            sql_connection.commit()

            main_challenge_id = True
            while main_challenge_id:
                main_challenge_id, challenge_attributes = await main_conn.get_current_challenge(main_assessment_id)

                if not main_challenge_id:
                    break
        
                attributes_parsed = urllib.parse.urlencode(challenge_attributes)


                correct_answer = '#ABAND#'
                if answer_cache[competence_id].get(attributes_parsed):
                    correct_answer = answer_cache[competence_id][attributes_parsed]

                else:
                    
                    print('resorting to sql database...')
                    sql_response = get_from_cache(competence_id,attributes_parsed)

                    if sql_response:
                        correct_answer = sql_response[0]
                        print('fetched:',correct_answer,sql_response)

                    else:
                        print('no answer found :c')
                        if IS_PERFECTIONIST:
                            break

                _, is_correct = await main_conn.answer_question(main_challenge_id,main_assessment_id,correct_answer)
                if not is_correct:
                    print('put an answer in, but its wrong???')
                    print(correct_answer)
                    print(challenge_attributes)
                else:
                    print('put a CORRECT answer in!!!')
    sql_connection.close()           





asyncio.run(main())