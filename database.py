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

# Retrieve existing summarized data for a user
def get_existing_summarized_data(user_id):
    connection = get_mysql_connection()
    cursor = connection.cursor()

    query = "SELECT summarizedData FROM summarized_reports WHERE UserId = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()

    cursor.close()
    connection.close()

    if result:
        return json.loads(result[0])
    return None

# Save or update summarized data in MySQL
def save_summarized_data(user_id, summarized_data):
    connection = get_mysql_connection()
    cursor = connection.cursor()

    query = """
    INSERT INTO summarized_reports (UserId, summarizedData)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE summarizedData = %s, lastUpdated = NOW()
    """
    cursor.execute(query, (user_id, json.dumps(summarized_data), json.dumps(summarized_data)))

    connection.commit()
    cursor.close()
    connection.close()
