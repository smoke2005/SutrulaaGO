import base64
from flask import Flask, render_template, request, redirect, url_for, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.utils import secure_filename
from currency import (
    get_profile_id,
    create_virtual_card,
    get_wise_balance,
    fetch_exchange_rate,
    create_quote,
    get_balance_id
)
from sutrulaaIT import generate_itinerary_data 

app = Flask(__name__)
def image_to_base64(image_file):
    image_bytes = image_file.read()
    return base64.b64encode(image_bytes).decode('utf-8')

# Firebase setup
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/Users/SAIRAM/Desktop/sai tamizhi/sutrulaaGO/credentials/firebase-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/Itinerary')
def itinerary():
    print("Itinerary route accessed")  # Debug line
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

        # Initialize photo_url to None
        photo_url = None
        if photo:
            photo_url = image_to_base64(photo)  # Convert image to base64 string

        # Save the log in Firestore
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

# WISE API routes
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

# Itinerary recommendation route
@app.route("/generate-itinerary", methods=["POST"])
def generate_itinerary():
    data = request.get_json()
    lat = data['location']['lat']
    lon = data['location']['lon']
    days = data['days']
    interests = "sightseeing"

    # Call the imported function
    itinerary_text, travel_segments = generate_itinerary_data(lat, lon, days, interests)

    return jsonify({
        "itinerary": itinerary_text,
        "travel_info": travel_segments
    })

if __name__ == '__main__':
    app.run(debug=True)
