import pandas as pd
from datetime import timedelta, datetime
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Set Keepa API details
API_URL = "https://api.keepa.com/product?key={}&domain=1&asin={}"  # Adjust for your Keepa API
API_KEY = "fcb7li7tu6vcd85svgo1tao0opr2q3c0jmagjgk540q4ljjr7u14m9d0ae22e5hr"  # Replace with your actual Keepa API key

@app.route('/detect_ip_risk', methods=['POST'])
def analyze_data():
    # Extract ASIN from the request
    asin = request.json.get('asin')
    print(asin)
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
    print("Successfully fetched new offer count data.", new_offer_count_data is None)

    # Parse new offer count data
    print("Parsing new offer count data...")
    keepa_base = 21564000
    current_date = datetime.utcnow()
    cutoff_date = current_date - timedelta(days=365)  # Data for the last year

    parsed_data = []
    if new_offer_count_data is None:
        return jsonify({
            "pattern_one": 'false',
            "pattern_one_dates": [{'start_date': 'API have No data', 'end_date': 'API have No data'}],
            "pattern_two": 'false',
            "pattern_two_dates": [],
        })
    for i in range(0, len(new_offer_count_data), 2):  # Iterate over time-value pairs
        keepa_time = new_offer_count_data[i]
        value = new_offer_count_data[i + 1]

        # Convert Keepa time to a human-readable timestamp
        timestamp = (keepa_base + keepa_time) * 60
        current_converted_date = datetime.utcfromtimestamp(timestamp)
        if current_converted_date >= cutoff_date:
            parsed_data.append({
                "Date": current_converted_date.strftime('%Y-%m-%d %H:%M:%S'),
                "NewOfferCount": int(value)  # Convert to standard Python int
            })
    print(f'\n\nparsed_data: { parsed_data} \n\n')
    if not parsed_data:
        return jsonify({
            "pattern_one": 'false',
            "pattern_one_dates": [{'start_date': 'Short Data', 'end_date': 'Short Data'}],
            "pattern_two": 'false',
            "pattern_two_dates": [],
        })


    # Convert to DataFrame
    df = pd.DataFrame(parsed_data)
    df['Date'] = pd.to_datetime(df['Date'])  # Convert to datetime
    df['DateOnly'] = df['Date'].dt.date  # Extract date part (without time)

    # Step 1: Remove duplicate dates, keeping the one with the highest newOfferCount
    df_max = df.groupby('DateOnly', as_index=False)['NewOfferCount'].max()

    # Step 2: Fill missing dates
    start_date = df_max['DateOnly'].min()
    end_date = df_max['DateOnly'].max()
    date_range = pd.date_range(start=start_date, end=end_date).date

    filled_df = pd.DataFrame(date_range, columns=['DateOnly'])
    merged_df = pd.merge(filled_df, df_max, on='DateOnly', how='left')
    merged_df['NewOfferCount'].fillna(method='ffill', inplace=True)
    merged_df['NewOfferCount'] = merged_df['NewOfferCount'].astype(int)  # Ensure integer format
    merged_df['Date'] = pd.to_datetime(merged_df['DateOnly'])

    result = merged_df[['Date', 'NewOfferCount']]

    # --- Pattern One: Rigid Periods (30 Days Same Offer Count) ---
    pattern_one_dates = []
    for i in range(len(merged_df) - 30):
        current_value = int(merged_df.iloc[i]['NewOfferCount'])  # Convert to int
        end_date = merged_df.iloc[i + 30]['Date']
        if all(int(merged_df.iloc[j]['NewOfferCount']) == current_value for j in range(i, i + 30)):
            pattern_one_dates.append({
                "start_date": merged_df.iloc[i]['Date'].strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "constant_value": current_value
            })

    # --- Pattern Two: Drops of 5 or More Sellers in 3 Days ---
    pattern_two_dates = []
    for i in range(len(merged_df) - 3):
        start_value = int(merged_df.iloc[i]['NewOfferCount'])  # Convert to int
        start_date = merged_df.iloc[i]['Date']
        for j in range(i + 1, i + 4):
            end_value = int(merged_df.iloc[j]['NewOfferCount'])  # Convert to int
            end_date = merged_df.iloc[j]['Date']
            if start_value - end_value >= 5:  # Drop threshold
                pattern_two_dates.append({
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "dropped_from": start_value,
                    "dropped_to": end_value
                })
                break  # Stop at the first drop within 3 days

    # Final result with both patterns
    final_result = {
        "pattern_one": 'true' if pattern_one_dates else 'false',
        "pattern_one_dates": [{  
            "start_date": d["start_date"], 
            "end_date": d["end_date"],
            "constant_value": int(d["constant_value"])  # Ensure int
        } for d in pattern_one_dates],
        "pattern_two": 'true' if pattern_two_dates else 'false',
        "pattern_two_dates": [{  
            "start_date": d["start_date"], 
            "end_date": d["end_date"],
            "dropped_from": int(d["dropped_from"]),  # Ensure int
            "dropped_to": int(d["dropped_to"])  # Ensure int
        } for d in pattern_two_dates],
    }

    print("Final Result:", final_result)

    return jsonify(final_result)

if __name__ == '__main__':
    app.run(debug=True)
