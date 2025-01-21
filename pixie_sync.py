#what if i cry

import requests
import urllib.parse
import urllib3  


import random

ssl = False
LANG = 'fr'

if not ssl:
    urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)


def random_hash():
    return "%016x" % random.getrandbits(64)



class PixConnection:

    def __init__(self,auth_token=''):
        self.auth_token = auth_token

    
    def get_headers(self):
        return {
            "authorization": f"Bearer {self.auth_token}",
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'accept-language': LANG,
        }

    def get_login_headers(self):
        #yes, they're different
        return {
            "content-type": "application/x-www-form-urlencoded",
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',

        }

    def get(self,url):
        response = requests.get(verify=ssl, url=url,headers= self.get_headers())
        return response.json()

    def patch(self,url,payload=None,data=None,headers=None):
        if not headers:
            headers = self.get_headers()
        response = requests.patch(url,verify=ssl,json=payload,data=data,headers=headers)

        return response.text
    
    def post(self,url,payload=None,data=None,headers=None):
        if not headers:
            headers = self.get_headers()
        response = requests.post(url,verify=ssl,json=payload,data=data,headers=headers)

        return response.json()

    def signup(self, first_name, last_name, email, password):
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
                    "lang":LANG,
                    "locale":None,
                    "is-anonymous":False,
                    "should-see-data-protection-policy-information-banner":False,
                    "email-confirmed":True
                },
            "type":"users"
            }
        }
        url = 'https://app.pix.org/api/users'
        response = self.post(url,payload)
        if response.get('errors'):
            if response['errors'][0]['detail'] == 'INVALID_OR_ALREADY_USED_EMAIL':
                print('email already exists, still trying to login...')
        return self.login(email,password)

    def signup_random_account(self):
        first_name = random_hash()
        last_name = random_hash()

        email = random_hash() + '@chickenattack.org'
        password = '1@aA' + random_hash()
        return self.signup(first_name,last_name,email,password)

    def login(self,email,password):
        url = 'https://app.pix.org/api/token'
        params = {
            'grant_type': 'password',
            'username': email,
            'password': password,
            'scope': 'mon-pix'
        }
        response = self.post(url,data=params,headers=self.get_login_headers())
        access_token = response['access_token']
        self.auth_token = access_token
        print('LOGIN SUCCESSFUL',  access_token[0:5] + '***' + access_token[-5:])
        return access_token


    def get_user_id(self):
        me_url = 'https://app.pix.org/api/users/me'

        me = self.get(me_url)['data']

        return me['id']
    

    '''() -> competence ids'''
    def get_competences(self):
        user_id = self.get_user_id()

        profile_url = f'https://app.pix.org/api/users/{user_id}/profile'

        data = self.get(profile_url)

        response = []
        for included in data['included']:
            if included['type'] == 'scorecards':
                response.append(included['id'].split('_')[1])
        return response
   

    '''competence id -> assessment id'''
    def start_or_resume(self,competence_id):
        url = 'https://app.pix.org/api/competence-evaluations/start-or-resume'

        payload = {
            'competenceId': competence_id
        }

        data = self.post(url,payload)['data']

        return data['relationships']['assessment']['data']['id']


    '''assessment id -> challenge id, attributes'''
    def get_current_challenge(self,assessment_id):
        url = f'https://app.pix.org/api/assessments/{assessment_id}/next'
        
        data = self.get(url)['data']

        if not data:
            return None, None

        challenge_id = data['id']


        return challenge_id , data['attributes']
    
    

    '''challenge id + assessment id + answer attempt -> answer id, answer correctness'''
    def answer_question(self,challenge_id, assessment_id,value): #returns an answer id you can use later for corrections
        url = f'https://app.pix.org/api/answers'
        payload = {
            "data":{
                "attributes":{
                    "value":value,
                    "result":None,
                    "result-details":None,
                    "timeout":10,
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
       
        response = self.post(url,payload)
        

        response = response['data']
        
        answer_id = response['id']

        is_correct = True if response['attributes']['result'] == 'ok' else False

        return answer_id, is_correct
    
    '''answer id -> answer correction'''
    def get_correction(self,answer_id):
        url = f'https://app.pix.org/api/answers/{answer_id}/correction'
        response = self.get(url)
        
        if response.get('errors'):
            return [ ] #doesn't exist

        solution = response['data']['attributes']['solution'].split('\n')

        return solution
    
    def complete_assessment(self,assessment_id):
        payload = {
            "data":{
                "id":assessment_id,
                "attributes":{
                    "certification-number":None,
                    "code-campaign":None,
                    "state":"started",
                    "title":"Resolving technical problems",
                    "type":"COMPETENCE_EVALUATION",
                    "last-question-state":"asked",
                    "method":"SMART_RANDOM",
                    "has-ongoing-challenge-live-alert":None,
                    "has-ongoing-companion-live-alert":None,
                    "competence-id":"recIhdrmCuEmCDAzj"
                },
                "relationships":{
                    "course":{
                        "data":{
                            "type":"courses",
                            "id":"[NOT USED] CompetenceId is in Competence Evaluation."
                        }
                    },
                    "progression":{
                        "data":None
                        }
                },
                "type":"assessments"
                }
            }
        url = f'https://app.pix.org/api/assessments/{assessment_id}/complete-assessment'

        return self.patch(url=url,payload=payload)
