import streamlit as st
import os
import easyocr
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import json
import requests  # Import requests for making API calls
from database import save_to_mysql 
import analysis

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API
genai.configure(api_key=os.getenv("API_KEY"))

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

# Streamlit UI
st.title("Blood Test Report Analyzer")

uploaded_file = st.file_uploader("Choose a file", type=["pdf", "jpg", "png"])

def extract_text_from_pdf(pdf_file):
    import fitz  # PyMuPDF
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in pdf_document:
        text += page.get_text()
    return text

def extract_text_from_image(image_file):
    image = Image.open(image_file)
    results = reader.readtext(image)
    return ' '.join([result[1] for result in results])

# def convert_text_to_json(text):
    prompt = f"Convert the following blood test report to a JSON format with key-value pairs:\n\n{text}"
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"},
        system_instruction="You are supposed to return me a json having two keys - reportMetrics like wbc,rbc etc and testDate. The value of reportMetric keys is json containing 4 properties : upperBound,lowerBound,unit of measurement,value present in patient's blood. The value of testDate key contains the date on which test was conducted in yyyy-mm-dd format.YOU MUST RETURN JSON ONLY. DONT GIVE ANY TEXT APART FROM JSON",
    )
    response = model.generate_content(prompt)
    return response.text  # Adjust this line based on the response format

def convert_text_to_json(text):
    prompt = f"""Convert the following blood test report to a JSON format with key-value pairs:

    {text}
    
    The JSON output should have the following structure:
    - "reportMetrics": an array of objects, where each object represents a metric with the following properties:
        - "testName": the name of the test (e.g., "WBC", "RBC")
        - "upperBound": the upper limit of the normal range
        - "lowerBound": the lower limit of the normal range
        - "unit": the unit of measurement
        - "value": the value present in the patient's blood
    - "testDate": the date on which the test was conducted in "yyyy-mm-dd" format. If the date is not available, return null.

    Example output:
    {{
        "reportMetrics": [
            {{
                "testName": "WBC",
                "upperBound": "10.8",
                "lowerBound": "3.8",
                "unit": "Thousand/uL",
                "value": "3.9"
            }},
            {{
                "testName": "RBC",
                "upperBound": "5.80",
                "lowerBound": "4.20",
                "unit": "Million/uL",
                "value": "5.24"
            }}
            // ...more metrics
        ],
        "testDate": "2023-09-09"  // or null if the date is missing
    }}

    Return JSON only. Do not provide any text other than JSON.
    """
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"},
        system_instruction="You are supposed to return me a JSON as specified in the prompt. You must include a 'testName' field in each metric object. Return JSON only. Do not provide any text apart from JSON.",
    )
    response = model.generate_content(prompt)
    return response.text  # Adjust this line based on the response format


# Process the uploaded file
if uploaded_file:
    if uploaded_file.type == "application/pdf":
        text = extract_text_from_pdf(uploaded_file)
    else:
        text = extract_text_from_image(uploaded_file)
    
    # Convert the extracted text to JSON
    json_data = convert_text_to_json(text)

    # Convert json_data to json from json string
    json_data_json = json.loads(json_data)
    
    # Store the JSON data in MySQL with UserId = 2
    save_to_mysql(2, json_data, json_data_json.get("testDate"))
    
    st.success("Report saved successfully!")

# New Feature: API Call to Fetch Reports and Visualizations
user_id_input = st.number_input("Enter User ID", min_value=1)
if st.button("Get Report from API"):
    try:
        # API endpoint to fetch report data and visualizations
        api_url = "http://localhost:5000/api/getReports"
        
        # API request payload
        payload = {"userId": user_id_input}
        
        # Make POST request to the API to fetch report data and visualization
        response = requests.post(api_url, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        if response.status_code == 200:
            data = response.json()
            
            if "reportData" in data:
                st.write("Report Data:", data["reportData"])
            
            if "visualization" in data:
                st.image(data["visualization"], caption='Blood Test Results Visualization')
            else:
                st.error("Failed to fetch visualization.")
        else:
            st.error(f"Failed to fetch report. Status code: {response.status_code}")
    
    except requests.RequestException as e:
        st.error(f"Error making API request: {e}")