import mysql.connector
import json
import os

# MySQL Connection Function
def get_mysql_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT"))
    )

def save_to_mysql(user_id, json_data, testDate):
    connection = get_mysql_connection()
    cursor = connection.cursor()

    query = """
    INSERT INTO reports (UserId, reportDetails, testDate)
    VALUES (%s, %s, STR_TO_DATE(%s, '%Y-%m-%d'))
    """
    cursor.execute(query, (user_id, json_data, testDate))

    connection.commit()
    cursor.close()
    connection.close()
