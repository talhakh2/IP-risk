import openai
from flask import Flask, request, jsonify
import pandas as pd
from datetime import datetime, timedelta
import requests
from flask_cors import CORS
import json, re

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# API Keys and URLs
API_KEY = 'fcb7li7tu6vcd85svgo1tao0opr2q3c0jmagjgk540q4ljjr7u14m9d0ae22e5hr'
API_URL = 'https://api.keepa.com/product?key={}&domain=1&asin={}'

OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

# Constants
MAX_TOKENS = 1000
CHUNK_SIZE = 30

def call_chatgpt(prompt, model="gpt-4", max_tokens=1000):
    """
    Calls the OpenAI ChatGPT API with the given prompt and returns the response.
    """
    try:
        # Define the system instructions
        system_instructions = (
            "The following dataset includes sequential dates from the past year with their corresponding new offer count. "
            "Only dates with changes in the new offer count are present - any date not present in this data signifies that there were no changes in the new offer count for that specific date \n"
            "You are an expert data analyst. Your task is to identify specific patterns from the provided sales data, "
            "and clearly indicate when such patterns are detected. The analysis should focus on the following two patterns:\n"
            "\n"
            "1. **Consistent new offer count (Completely Rigid for 30+ Days)**:\n"
            "   - Identify periods where the new offer count remains completely rigid for **30 consecutive days or more**.\n"
            "   - Example: The new offer count stays at the same value with no movement up or down, resembling a straight line when visualized.\n"
            "   - Once detected, clearly indicate that this pattern has been identified and specify the period in which it occurred.\n"
            "\n"
            "2. **A drop of value having gap equal or greater than 5 in the newOfferCount, occurring within a 3-day timeframe**:\n"
            "   - For example: If the new offer count is 10 on 2024-10-09 and drops to 5 or more on 2024-10-11, count this as one identified pattern.\n"
            "   - However, if the total drop in newOfferCount is less than 5, than don't count it as identified. and not include that dates.\n"
            "   - Also, if the date range spans more than 3 days, don't count it as identified. and don't include that dates\n"
            "   - Pattern is only said to be qualified when both these cases, drop of count is 5+ in newOffercount and that drop is within timeperiod of 3-days.\n"
            "   - Once detected, clearly indicate that this pattern has been identified and specify the period in which it occurred, including the initial and after decreasing drop.\n"
            "\n"
            "### Output Requirements:\n"
            "- Return the detected patterns in JSON format with the following structure:\n"
            "{\n"
            "    \"pattern_one\": 'true/false',  # Whether Pattern 1 was detected. t and f should be small\n"
            "    \"pattern_one_dates\": [  # List of identified timeframes for Pattern 1\n"
            "        {\n"
            "            \"start_date\": \"\",  # The start date of the rigid period\n"
            "            \"end_date\": \"\"     # The end date of the rigid period\n"
            "        }\n"
            "    ],\n"
            "    \"pattern_two\": 'true/false',  # Whether Pattern 2 was detected. t and f should be smal\n"
            "    \"pattern_two_dates\": [  # List of identified timeframes for Pattern 2\n"
            "        {\n"
            "            \"start_date\": \"\",  # The start date of the drop\n"
            "            \"end_date\": \"\",    # The end date of the drop\n"
            "            \"dropped_from\": \"\",         # Total number of sellers initally\n"
            "            \"dropped_to\": \"\"         # Total number of sellers after decreasing\n"
            "        }\n"
            "    ]\n"
            "}\n"
            "\n"
            "### Notes:\n"
            "- If no patterns are detected, return false for the respective pattern and an empty list for the corresponding dates.\n"
            "- Ensure your analysis is detailed, and explicitly state how each detected pattern aligns with the given criteria.\n"
            "- This analysis is too critical. So, find patterns accuratley and match patterns exactly as mentioned. There should'nt be any error."
        )


        # Make the API call
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        
        # Extract and return the assistant's response
        return response['choices'][0]['message']['content']
    
    except Exception as e:
        # Return detailed error information
        return f"Error calling ChatGPT: {e}"

def chunk_data(data, chunk_size):
    """
    Splits data into smaller chunks for processing.
    """
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

@app.route('/detect_ip_risk', methods=['POST'])
def analyze_data():
    """
    Analyzes the new offer count data for a given ASIN and detects patterns using ChatGPT.
    """
    try:

        # Initialize variables to avoid access errors
        pattern_one = 'false'
        pattern_two = 'false'
        # Extract ASIN from the request
        asin = request.json.get('asin')
        if not asin:
            return jsonify({'error': 'ASIN is required'}), 400

        print(f"Starting analysis for ASIN: {asin}")

        # Fetch Keepa data
        print("Fetching data from Keepa API...")
        response = requests.get(API_URL.format(API_KEY, asin))
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch data from Keepa API'}), 500

        keepa_data = response.json()
        if 'products' not in keepa_data or len(keepa_data['products']) == 0:
            return jsonify({'error': 'No products found for the given ASIN'}), 404

        # Extract new offer count data
        product_data = keepa_data['products'][0]
        if 'csv' not in product_data or len(product_data['csv']) <= 11:
            return jsonify({'error': 'New offer count data is missing'}), 404

        new_offer_count_data = product_data['csv'][11]
        print("Successfully fetched new offer count data.")

        # Parse new offer count data
        print("Parsing new offer count data...")
        keepa_base = 21564000
        current_date = datetime.utcnow()
        cutoff_date = current_date - timedelta(days=365)  # Data for the last year

        parsed_data = []
        for i in range(0, len(new_offer_count_data), 2):  # Iterate over time-value pairs
            keepa_time = new_offer_count_data[i]
            value = new_offer_count_data[i + 1]

            # Convert Keepa time to a human-readable timestamp
            timestamp = (keepa_base + keepa_time) * 60
            current_converted_date = datetime.utcfromtimestamp(timestamp)
            if current_converted_date >= cutoff_date:
                parsed_data.append({"Date": current_converted_date.strftime('%Y-%m-%d %H:%M:%S'), "NewOfferCount": value})

        if not parsed_data:
            print('Data is short')
            return jsonify({
                "pattern_one": 'false',
                "pattern_one_dates": [{'start_date': 'Short Data', 'end_date': 'Short Data'}],
                "pattern_two": 'false',
                "pattern_two_dates": [],
            })

        print(f"Parsed {len(parsed_data)} data points for analysis.")

        # Split data into chunks for ChatGPT
        print("Splitting data into chunks...")
        chunks = list(chunk_data(parsed_data, CHUNK_SIZE))
        context = f"ASIN: {asin}, Time period: {parsed_data[0]['Date']} to {parsed_data[-1]['Date']}"
        final_results = []

        # Analyze each chunk with ChatGPT
        print("Analyzing data chunks with ChatGPT...")
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i + 1} of {len(chunks)}...")

            # Format chunk data for ChatGPT
            chunk_data_str = "\n".join([f"Date: {item['Date']}, New Offer Count: {item['NewOfferCount']}" for item in chunk])
        
            prompt = f"""
            You are an expert data analyst.

            ### Context:
            {context}

            ### Data:
            {chunk_data_str}

            Return data in proper format as mentioned in instructions.
            
            """

            
            # Call ChatGPT
            chunk_response = call_chatgpt(prompt)
            print(f"Chunk {i + 1} Response: {chunk_response}")

            # Extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', chunk_response)
            if json_match:
                try:
                    json_str = json_match.group()
                    chunk_result = json.loads(json_str)
                    final_results.append(chunk_result)

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON for chunk {i + 1}: {e}")
                except Exception as e:
                    print(f"Error processing chunk {i + 1}: {e}")
            else:
                print(f"No JSON response found in chunk {i + 1}")

        # Aggregate results
        print("Aggregating results...")
        dates_one = []
        dates_two = []
        for result in final_results:
            if result:  # Ensure result is not None
                dates_one.extend(result.get('pattern_one_dates', []))
                dates_two.extend(result.get('pattern_two_dates', []))

        if len(dates_one) > 0:
            pattern_one = 'true'

        if len(dates_two) > 0:
            pattern_two = 'true'

        print({
            "pattern_one": pattern_one,
            "pattern_one_dates": dates_one,
            "pattern_two": pattern_two,
            "pattern_two_dates": dates_two
        })

        print("Analysis completed successfully.")
        return jsonify({
            "pattern_one": pattern_one,
            "pattern_one_dates": dates_one,
            "pattern_two": pattern_two,
            "pattern_two_dates": dates_two
        })

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True)