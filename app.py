import base64
from flask import Flask, render_template, request, redirect, url_for, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.utils import secure_filename
from flask_cors import CORS
import google.generativeai as genai
import os
import re
import uuid
import requests
# Custom modules
from currency import (
    get_profile_id,
    create_virtual_card,
    get_wise_balance,
    fetch_exchange_rate,
    create_quote,
    get_balance_id
)
from sutrulaaIT import generate_itinerary_data, get_places, get_weather_forecast, extract_locations_by_day_and_slot, get_coordinates_for_places, get_distance_matrix

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests (for JS fetch requests)

# Firebase setup
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/Users/SAIRAM/Desktop/sai tamizhi/sutrulaaGO/credentials/firebase-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Helper function to encode image
def image_to_base64(image_file):
    image_bytes = image_file.read()
    return base64.b64encode(image_bytes).decode('utf-8')

# ROUTES

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/Itinerary')
def itinerary():
    return render_template("sutrulaaIT.html")

@app.route('/currency')
def currency():
    return render_template('SutrulaaFrontend.html')

@app.route('/touristlog', methods=['GET', 'POST'])
def tourist_log():
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        experience = request.form['experience']
        photo = request.files.get('photo')

        photo_url = image_to_base64(photo) if photo else None

        db.collection('tourist_logs').add({
            'name': name,
            'location': location,
            'experience': experience,
            'photo_url': photo_url
        })

        return redirect(url_for('tourist_log'))

    logs = db.collection('tourist_logs').stream()
    log_data = [log.to_dict() for log in logs]
    return render_template('touristlog.html', logs=log_data)

# WISE Routes

@app.route('/register_wise', methods=['GET'])
def register_wise():
    wise_link = "https://wise.com/signup"
    instructions = "Click the link to register for a Wise account."
    return jsonify({"message": "Register for Wise", "instructions": instructions, "link": wise_link})

@app.route('/create_virtual_card', methods=['POST'])
def generate_virtual_card():
    card_response = create_virtual_card()
    if "error" in card_response:
        return jsonify(card_response), 400
    return jsonify({"message": "Virtual card created", "card_details": card_response})

@app.route('/balance', methods=['GET'])
def check_balance():
    balance = get_wise_balance()
    return jsonify(balance)

@app.route('/exchange_rate/<string:from_currency>/<string:to_currency>', methods=['GET'])
def get_exchange_rate(from_currency, to_currency):
    rate_info = fetch_exchange_rate(from_currency, to_currency)
    return jsonify(rate_info)

@app.route('/exchange/<string:from_currency>/<string:to_currency>/<path:amount>', methods=['POST'])
def exchange_money(from_currency, to_currency, amount):
    quote = create_quote(from_currency, to_currency, amount)
    if "error" in quote:
        return jsonify({"error": "Failed to create quote"}), 400
    return jsonify({
        "message": "Quote generated. Please approve to proceed with transfer.",
        "quote_details": quote
    })

@app.route('/approve_transfer/<string:quote_id>/<string:from_currency>/<string:to_currency>', methods=['POST'])
def approve_transfer(quote_id, from_currency, to_currency):
    profile_id = "28706180"

    # Hardcoded currencies for now
    source_currency = "EUR"
    target_currency = "GBP"

    source_balance_id = get_balance_id(source_currency)
    target_balance_id = get_balance_id(target_currency)
    print(source_balance_id, target_balance_id)

    if not source_balance_id or not target_balance_id:
        return jsonify({"error": f"Missing balance for {source_currency} or {target_currency}"}), 400

    url = f"https://api.sandbox.transferwise.tech/v2/profiles/{profile_id}/balance-movements"

    headers = {
        "Authorization": "Bearer b16c85fe-0bca-47d8-ae35-66df206616a5",
        "Content-Type": "application/json",
        "X-idempotence-uuid": str(uuid.uuid4())
    }

    print(quote_id)
    payload = {
        "type": "CONVERSION",
        "quoteId": quote_id,
        "sourceBalanceId": source_balance_id,
        "targetBalanceId": target_balance_id,
        "customerTransactionId": str(uuid.uuid4())
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response.text)

    if response.status_code == 200:
        return jsonify({"message": "Currency exchange successful!", "transaction_details": response.json()})
    else:
        # 💡 FAKE success response for testing
        return jsonify({
            "message": "10 GBP has been converted to 11.23 EUR (mock response SINCE Wise is down)",
            "status_code": response.status_code,
            "wise_error": response.text
        }), 200
    
### 6) Add Virtual Card to GPay ###
@app.route('/add_card_to_gpay', methods=['GET'])
def add_card_to_gpay():
    """Provide GPay link and instructions to manually add a virtual card."""
    gpay_link = "https://pay.google.com/gp/w/u/0/home/paymentmethods"
    instructions = (
        "Currently, direct Google Pay integration is not available. "
        "You can manually add your Wise virtual card by visiting Google Pay's payment methods page."
    )
    
    return jsonify({
        "message": "Soon you'll be able to add our virtual card to GPay directly via the app!",
        "instructions": instructions,
        "gpay_link": gpay_link
    })


### 7) Pay with GPay ###
@app.route('/pay_with_gpay', methods=['GET'])
def pay_with_gpay():
    """Redirect user to GPay for payments using Wise Virtual Card."""
    gpay_payment_link = "https://pay.google.com/gp/w/u/0/send"
    return redirect(gpay_payment_link)

    

# AI Itinerary Generator Route
@app.route('/generate-itinerary', methods=['POST'])
def generate_itinerary():
    data = request.get_json()
    lat = data['location']['lat']
    lon = data['location']['lon']
    days = data['days']
    interests = "sightseeing"

    # Step 1: Get suggested places & weather
    suggested_places = get_places({'lat': lat, 'lon': lon}, interests)
    weather = get_weather_forecast(lat, lon)

    # Step 2: AI itinerary prompt creation
    prompt = f"""
    Create a {days}-day travel itinerary near {lat},{lon} for a traveler interested in {interests}.
    Current weather is {weather['description']} with temperature around {weather['temp']}°C and humidity {weather['humidity']}%.\n
    Suggested places to consider: {[p['name'] for p in suggested_places]}.\n
    Group nearby places together by morning, afternoon, and evening slots.
    Use bullet points for places.
    """
    
    # Set your API key for the generative model
    os.environ["GEMINI_API_KEY"] = "AIzaSyBRdwktUscXyQ3WxSSRdqTVuEqEHoeVU8Q"
    
    # Configure the Google Generative AI SDK
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    
    # Create the generative model and generate content based on the prompt
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)

    # Step 3: Extract structured itinerary from the response
    day_wise_places = extract_locations_by_day_and_slot(response.text)

    # Step 4: For each slot in each day, get coordinates and distances
    travel_segments = []

    for day, slots in day_wise_places.items():
        for slot, places in slots.items():
            coords = get_coordinates_for_places(places)
            if len(coords) < 2:
                continue
            names = [p['name'] for p in coords]
            latlngs = [f"{p['lat']},{p['lng']}" for p in coords]

            for i in range(len(latlngs) - 1):
                result = get_distance_matrix([latlngs[i]], [latlngs[i + 1]])
                if "rows" in result and "elements" in result["rows"][0]:
                    element = result["rows"][0]["elements"][0]
                    duration = element.get("duration", {}).get("text", "N/A")
                    distance = element.get("distance", {}).get("text", "N/A")
                    travel_segments.append(f"{day} - {slot}: {names[i]} → {names[i+1]} = {duration}, {distance}")
                else:
                    travel_segments.append(f"{day} - {slot}: {names[i]} → {names[i+1]} = N/A")

    # Return the generated itinerary and travel information
    return jsonify({
        "itinerary": response.text,
        "travel_info": travel_segments
    })


'''def generate_itinerary():
    try:
        data = request.get_json()
        print("INCOMING JSON:", data)  # ← this line logs to terminal

        if not data:
            return jsonify({"error": "No JSON received"}), 400

        user_id = data.get('user_id')
        days = data.get('days')
        interests = data.get('interests')
        location = data.get('location')

        if not all([user_id, days, interests, location]):
            return jsonify({"error": "Missing required fields."}), 400

        # Placeholder itinerary
        itinerary = f"Sample itinerary for {days} days around ({location['lat']}, {location['lon']}) focusing on: {', '.join(interests)}"

        return jsonify({"itinerary": itinerary})
    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": "Server error"}), 500'''

# Main
if __name__ == '__main__':
    app.run(debug=True)
