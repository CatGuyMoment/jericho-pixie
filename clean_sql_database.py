import sqlite3
import urllib
from pixie_sync import PixConnection

competences = ['recsvLz0W2ShyfD63', 'recIkYm646lrGvLNT', 'recNv8qhaY887jQb2', 'recDH19F7kKrfL3Ii', 'recgxqQfz3BqEbtzh', 'recMiZPNl7V1hyE1d', 'recFpYXCKcyhLI3Nu', 'recOdC9UDVJbAXHAm', 'recbDTF8KwupqkeZ6', 'recHmIWG6D0huq6Kx', 'rece6jYwH4WEw549z', 'rec6rHqas39zvLZep', 'recofJCxg0NqTqTdP', 'recfr0ax8XrfvJ3ER', 'recIhdrmCuEmCDAzj', 'recudHE5Omrr10qrx']

connection = sqlite3.connect('answers_save.db')

cursor = connection.cursor()

def get_from_cache(competence_id):
    sql = cursor.execute(f'SELECT * FROM {competence_id}' )
    return sql.fetchall()

def insert_into_cache(competence_id,attributes,answer):

    answer = answer.replace('"','""') #escaping the quotation marks
    # print(f'INSERT INTO {competence_id} VALUES ( "{attributes}", "{answer}"  )')
    cursor.execute(f'REPLACE INTO {competence_id} VALUES ( "{attributes}", "{answer}"  )')

for competence_id in competences:
    data = get_from_cache(competence_id)

    for attributes, answer in data:
        decoded_attributes = dict(urllib.parse.parse_qsl(attributes))
        if '\n' in answer and not 'QROCM' in decoded_attributes['type']:
            new_answer = answer.split('\n')[0]
            insert_into_cache(competence_id,attributes,new_answer)

connection.commit()