#what if i cry

# import requests
import urllib.parse

import random

import asyncio

import base64
import json 
import aiohttp

import socket

SSL = False
def random_hash():
    return "%016x" % random.getrandbits(64)


class PixConnection:

    def __init__(self,aiohttp_session=None,auth_token=''):
        self.auth_token = auth_token
        self.session = aiohttp_session
    
    def change_session(self,aiohttp_session):
        self.session = aiohttp_session

    def get_headers(self):
        header = {
            # "authorization": f"Bearer {self.auth_token}",
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            # 'Accept': '*/*',
            # 'Accept-Encoding': 'gzip, deflate, br',
            # 'content-type': 'application/json',
            'accept-language': 'en',

           
        }
        if self.auth_token:
            header['authorization'] = f"Bearer {self.auth_token}"
        return header

    def get_login_headers(self):
        #yes, they're different
        return {
            "content-type": "application/x-www-form-urlencoded",
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            

        }

    async def get(self,url):
        #httpx implementation
        # response = await self.session.get(url=url,headers=self.get_headers())
        # return response.json()

        #aiohttp implementation
        async with self.session.get(ssl=SSL,url=url,headers=self.get_headers()) as response:
                if response.headers['Content-Type'] == 'text/html':
                    print(response.request_info.headers)
                    print(await response.text())
                return await response.json()


    async def post(self,url,payload=None,data=None,headers=None):

        #httpx implementation
        if not headers:
            headers = self.get_headers()
        # response = await self.session.post(url=url,json=payload,data=data,headers=headers)
        # return response.json()
    
        #aiohttp implementation

        async with self.session.post(ssl=SSL,url=url,json=payload,data=data,headers=headers) as response:
            if response.headers['Content-Type'] == 'text/html':
                    print(response.request_info.headers)
                    print(await response.text())
            return await response.json()

    async def signup(self, first_name, last_name, email, password):
        payload = {
            "data":{
                "attributes":{
                    "first-name":first_name,
                    "last-name": last_name,
                    "email":email,
                    "username":None,
                    "password":password,
                   "cgu":True,
                   "must-validate-terms-of-service":False,
                    "has-seen-assessment-instructions":False,
                   "has-seen-new-dashboard-info":False,
                    "has-seen-focused-challenge-tooltip":False,
                    "has-seen-other-challenges-tooltip":False,
                    "has-assessment-participations":False,
                    "has-recommended-trainings":False,
                    "code-for-last-profile-to-share":None,
                    "lang":"en",
                    "locale":None,
                    "is-anonymous":False,
                    "should-see-data-protection-policy-information-banner":False,
                    "email-confirmed":True
                },
            "type":"users"
            }
        }
        url = 'https://app.pix.org/api/users'
        
        response = await self.post(url,payload)
        if response.get('errors'):
            if response['errors'][0]['detail'] == 'INVALID_OR_ALREADY_USED_EMAIL':
                print('email already exists, still trying to login...')
        return await self.login(email,password)

    async def signup_random_account(self):
        first_name = random_hash()
        last_name = random_hash()

        email = random_hash() + '@chickenattack.org'
        password = '1@aA' + random_hash()
        return await self.signup(first_name,last_name,email,password)

    async def login(self,email,password):
        url = 'https://app.pix.org/api/token'
        params = {
            'grant_type': 'password',
            'username': email,
            'password': password,
            'scope': 'mon-pix'
        }
        response = await self.post(url,data=params,headers=self.get_login_headers())
        access_token = response['access_token']
        self.auth_token = access_token
        print('LOGIN SUCCESSFUL',  access_token[0:5] + '***' + access_token[-5:])
        return access_token

    
    '''() -> competence ids'''
    async def get_competences(self):
        user_id = str(json.loads(base64.b64decode(self.auth_token.split('.')[1]))['user_id'])

        profile_url = f'https://app.pix.org/api/users/{user_id}/profile'

        data = await self.get(profile_url)

        response = []
        for included in data['included']:
            if included['type'] == 'scorecards':
                response.append(included['id'].split('_')[1])
        return response
   

    '''competence id -> assessment id'''
    async def start_or_resume(self,competence_id):
        url = 'https://app.pix.org/api/competence-evaluations/start-or-resume'

        payload = {
            'competenceId': competence_id
        }

        data = (await self.post(url,payload) )['data']

        return data['relationships']['assessment']['data']['id']


    '''assessment id -> challenge id, attributes'''
    async def get_current_challenge(self,assessment_id):
        url = f'https://app.pix.org/api/assessments/{assessment_id}/next'
        
        data = (await self.get(url) )['data']
    
        
        if not data:
            return None, None
        

        challenge_id = data['id']


        return challenge_id , data['attributes']
    
    

    '''challenge id + assessment id + answer attempt -> answer id, answer correctness'''
    async def answer_question(self,challenge_id, assessment_id,value): #returns an answer id you can use later for corrections
        url = f'https://app.pix.org/api/answers'
        payload = {
            "data":{
                "attributes":{
                    "value":value,
                    "result":None,
                    "result-details":None,
                    "timeout":None,
                    "focused-out":False
                },
                "relationships":{
                    "assessment":{
                        "data":{
                            "type":"assessments",
                            "id":assessment_id
                            }
                        },
                        "challenge":{
                            "data":{
                                "type":"challenges",
                                "id":challenge_id
                            }
                        }
                },
                "type":"answers"
            }
        }
       
        response = await self.post(url,payload)
        
        if response.get('errors'):
            print('errors??',response)
            return None,None

        response = response['data']
        
        answer_id = response['id']

        is_correct = True if response['attributes']['result'] == 'ok' else False

        return answer_id, is_correct
    
    '''answer id -> answer correction'''
    async def get_correction(self,answer_id):
        url = f'https://app.pix.org/api/answers/{answer_id}/correction'
        response = await self.get(url)
        
        if response.get('errors'):
            return '' #doesn't exist

        solution = response['data']['attributes']['solution']

        return solution


# async def test():
    
#     async with aiohttp.ClientSession(connector=aiohttp.TCPConnector()) as session:
#         pix_session = PixConnection(session)
#         await pix_session.signup_random_account()
#         print(await pix_session.get_competences())


# asyncio.run(test())