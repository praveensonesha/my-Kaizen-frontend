import matplotlib.pyplot as plt
import mysql.connector
import json
import requests

# MySQL Connection Function
def get_mysql_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT"))
    )

def fetch_report_data(user_id):
    try:
        api_url = "http://localhost:5000/api/getReports"
        response = requests.post(api_url, json={"userId": user_id})
        response.raise_for_status()
        records = response.json()
        if records:
            return json.loads(records[0]['reportDetails'])
        else:
            print("No records found.")
            return None
    except requests.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None

def generate_visualizations(json_data):
    if not json_data or 'reportMetrics' not in json_data:
        print("No valid report data found.")
        return None

    metrics = json_data['reportMetrics']
    plt.figure(figsize=(12, 8))
    
    for metric in metrics:
        test_name = metric['testName']
        value = float(metric['value'])
        upper_bound = float(metric['upperBound'])
        lower_bound = float(metric['lowerBound'])
        unit = metric['unit']

        # Plotting the metric value
        plt.bar(test_name, value, color='blue', edgecolor='black')

        # Adding color bands for danger zones
        plt.axhline(y=upper_bound, color='red', linestyle='--', label=f'{test_name} Upper Bound')
        plt.axhline(y=lower_bound, color='green', linestyle='--', label=f'{test_name} Lower Bound')

        # Display danger zones
        if value > upper_bound:
            plt.text(test_name, value, 'Danger Zone', color='red', fontsize=12, ha='center')
        elif value < lower_bound:
            plt.text(test_name, value, 'Danger Zone', color='green', fontsize=12, ha='center')

    plt.xlabel('Test')
    plt.ylabel('Value')
    plt.title('Blood Test Results with Danger Zones')
    plt.legend(loc='best')
    plt.tight_layout()

    # Save the plot
    file_path = 'visualization.png'
    plt.savefig(file_path)
    plt.close()

    return file_path

def main(user_id):
    # Fetch the report data
    json_data = fetch_report_data(user_id)
    
    if json_data:
        # Generate the visualization
        image_path = generate_visualizations(json_data)
        if image_path:
            print(f"Visualization saved to {image_path}")
        else:
            print("Failed to generate visualization.")
    else:
        print("No data to visualize.")