import streamlit as st
import os
import easyocr
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import numpy as np
import json
import requests  # Import requests for making API calls
from database import save_to_mysql, get_existing_summarized_data, save_summarized_data
import analysis
import io

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
    # image = Image.open(image_file)

    image = Image.open(io.BytesIO(image_file.read()))
    
    # Convert the PIL Image to a numpy array
    image_np = np.array(image)
    # Read text from the image using EasyOCR
    results = reader.readtext(image_np)
    # results = reader.readtext(image)
    return ' '.join([result[1] for result in results])

def convert_text_to_json(text):
    prompt = f"Convert the following blood test report to a JSON format with key-value pairs:\n\n{text}"
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"},
        system_instruction="You are supposed to return me a json having two keys - reportMetrics like wbc,rbc etc and testDate. The value of reportMetric keys is json containing 4 properties : upperBound,lowerBound,unit of measurement,value present in patient's blood. The value of testDate key contains the date on which test was conducted in yyyy-mm-dd format.YOU MUST RETURN JSON ONLY. DONT GIVE ANY TEXT APART FROM JSON",
    )
    response = model.generate_content(prompt)
    return response.text  # Adjust this line based on the response format


# def convert_text_to_json(text):
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

# New Function to merge new report data with existing summarized data
def merge_and_summarize_data(user_id, new_report_data):
    # Retrieve existing summarized data
    existing_data = get_existing_summarized_data(user_id)
    
    # Prepare the prompt for the generative AI model
    prompt = f"""
    Given the following new blood report data and the existing summarized data, merge them into a single summarized JSON format. 

    Existing summarized data:
    {json.dumps(existing_data)}

    New report data:
    {json.dumps(new_report_data)}

    The JSON output should have the following structure:
    - "testName": the name of the test (e.g., "LDL Cholesterol")
    - "latestResult": the latest result from the new report
    - "unit": the unit of measurement
    - "date": the date of the latest result in "dth Month yyyy" format
    - "normalRange": an array with the normal range [min, max]
    - "historicalData": an array of objects with date and value from previous reports

    Example output:
    {{
        "testName": "LDL Cholesterol",
        "latestResult": 160,
        "unit": "mg/dL",
        "date": "7th Nov 2023",
        "normalRange": [100, 129],
        "historicalData": [
            {{ "date": "SEPT", "value": 130 }},
            {{ "date": "OCT", "value": 145 }},
            {{ "date": "NOV", "value": 160 }}
        ]
    }}
    Return JSON only. Do not provide any text other than JSON.
    """
    # Prepare the prompt for the generative AI model
    prompt = f"""
    Given the following new blood report data and the existing summarized data, merge them into a single summarized JSON format.

    Existing summarized data:
    {json.dumps(existing_data)}

    New report data:
    {json.dumps(new_report_data)}

    The JSON output should have the following structure:
    - "testName": the name of the test (e.g., "LDL Cholesterol")
    - "latestResult": the latest result from the new report and if the there result in new report then keep old values only
    - "unit": the unit of measurement
    - "date": the date of the latest result in "dth Month yyyy" format
    - "normalRange": an array with the normal range [min, max]
    - "historicalData": an array of objects with date and value from both existing and new reports

    **Rules for merging:**
    - If a test name already exists in the existing data, append the new result to the `historicalData` array, ensuring that the most recent result is marked as `latestResult` and that the data is ordered by date.
    - If a test name does not exist in the existing data, add it as a new entry with the new report data.
    - The `historicalData` should include both old and new values, sorted chronologically.

    Example output:
    {{
        "testName": "Platelet Count",
        "latestResult": 200000,
        "unit": "mg/dL",
        "date": "23rd Dec 2023",
        "normalRange": [150000, 410000],
        "historicalData": [
            {{ "date": "12th Dec 2023", "value": 150000 }},
            {{ "date": "23rd Dec 2023", "value": 200000 }}
        ]
    }}

    Return JSON only. Do not provide any text other than JSON.
    """
    # Configure the generative AI model
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"},
        system_instruction="You are supposed to merge and format the data as specified in the prompt. Return JSON only. Do not provide any text other than JSON.",
    )
    response = model.generate_content(prompt)

    merged_data = json.loads(response.text)  # Adjust this line based on the response format

    # Save the merged summarized data into the database
    save_summarized_data(user_id, merged_data)

    return merged_data

# Process the uploaded file
if uploaded_file:
    if uploaded_file.type == "application/pdf":
        text = extract_text_from_pdf(uploaded_file)
    else:
        text = extract_text_from_image(uploaded_file)
    
    # Convert the extracted text to JSON
    json_data = convert_text_to_json(text)


    # Convert json_data to json from json string
    new_report_data = json.loads(json_data)
    # json_data_json = json.loads(json_data)
    
    # Store the JSON data in MySQL with UserId = 2
    save_to_mysql(2, json_data, new_report_data.get("testDate"))
    
    # Merge new report data with existing summarized data
    merged_data = merge_and_summarize_data(2, new_report_data)

    st.success("Report saved successfully!")
    st.write("Merged Data:", merged_data)
