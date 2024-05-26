from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

conf = credentials.Certificate(r"D:\Rentify\cred.json")
firebase_admin.initialize_app(conf)
db = firestore.client()

@app.route('/')
def home():
    return render_template('welcome.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_data = request.json
        new_user = {
            "first_name": user_data['first_name'],
            "last_name": user_data['last_name'],
            "email": user_data['email'],
            "phone_number": user_data['phone_number'],
            "user_type": user_data['user_type'],
            "password": user_data['password']
        }
        db.collection('users').add(new_user)
        return jsonify({"message": "User registered successfully"}), 201
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_data = request.json
        user_query = db.collection('users').where('email', '==', login_data['email']).stream()
        existing_user = None
        for user_doc in user_query:
            existing_user = user_doc.to_dict()
            break
        print(existing_user)
        if existing_user and existing_user['password'] == login_data['password']:
            session['user'] = existing_user
            return jsonify({"message": "Login successful", "user_type": existing_user['user_type']}), 200

        return jsonify({"message": "Invalid credentials"}), 401
    return render_template('login.html')

@app.route('/shome')
def seller_home():
    return render_template('shome.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/post_property', methods=['GET', 'POST'])
def post_property():
    if 'user' not in session or session['user']['user_type'] != 'seller':
        return redirect(url_for('login'))

    if request.method == 'POST':
        property_info = request.json
        new_property = {
            "owner_id": session['user']['email'],
            "location": property_info['place'],
            "area": property_info['area'],
            "bedrooms": property_info['bedrooms'],
            "bathrooms": property_info['bathrooms'],
            "amenities": property_info['amenities'],
            "rent": property_info['rent'],
            "description": property_info['description']
        }
        db.collection('properties').add(new_property)
        return jsonify({"message": "Property posted successfully"}), 201

    return render_template('post_property.html')

@app.route('/list_properties', methods=['GET'])
def list_properties():
    if 'user' not in session or session['user']['user_type'] != 'buyer':
        return redirect(url_for('login'))

    user_properties = db.collection('properties').where('owner_id', '==', session['user']['email']).stream()
    properties_list = [prop.to_dict() for prop in user_properties]
    return render_template('view_properties.html', properties=properties_list)

@app.route('/my_properties', methods=['GET'])
def my_properties():
    if 'user' not in session or session['user']['user_type'] != 'seller':
        return redirect(url_for('login'))

    seller_properties = db.collection('properties').where('owner_id', '==', session['user']['email']).stream()
    seller_properties_list = [prop.to_dict() for prop in seller_properties]
    return render_template('view_properties_ss.html', properties=seller_properties_list)

@app.route('/update_property/<property_id>', methods=['GET', 'PUT'])
def update_property(property_id):
    if 'user' not in session or session['user']['user_type'] != 'seller':
        return redirect(url_for('login'))

    if request.method == 'PUT':
        update_data = request.json
        db.collection('properties').document(property_id).update(update_data)
        return jsonify({"message": "Property updated successfully"}), 200

    return render_template('update_property.html')

@app.route('/delete_property/<property_id>', methods=['DELETE'])
def delete_property(property_id):
    if 'user' not in session or session['user']['user_type'] != 'seller':
        return jsonify({"message": "Unauthorized"}), 403

    db.collection('properties').document(property_id).delete()
    return jsonify({"message": "Property deleted successfully"}), 200

@app.route('/properties', methods=['GET'])
def view_properties():
    all_properties = db.collection('properties').stream()
    properties_list = [prop.to_dict() for prop in all_properties]
    return jsonify(properties_list), 200

@app.route('/property_interest/<property_id>', methods=['GET'])
def property_interest(property_id):
    if 'user' not in session or session['user']['user_type'] != 'buyer':
        return jsonify({"message": "Unauthorized"}), 403

    property_doc = db.collection('properties').document(property_id).get()
    if property_doc.exists:
        owner_id = property_doc.to_dict()['owner_id']
        owner_query = db.collection('users').where('email', '==', owner_id).stream()
        owner_details = [owner.to_dict() for owner in owner_query]
        return jsonify(owner_details[0]), 200
    return jsonify({"message": "Property not found"}), 404

@app.route('/filter_properties', methods=['GET'])
def filter_properties():
    filter_params = request.args
    property_query = db.collection('properties')
    
    if 'place' in filter_params:
        property_query = property_query.where('location', '==', filter_params['place'])
    if 'min_rent' in filter_params and 'max_rent' in filter_params:
        property_query = property_query.where('rent', '>=', int(filter_params['min_rent'])).where('rent', '<=', int(filter_params['max_rent']))
    if 'bedrooms' in filter_params:
        property_query = property_query.where('bedrooms', '==', int(filter_params['bedrooms']))
    
    filtered_properties = property_query.stream()
    filtered_properties_list = [prop.to_dict() for prop in filtered_properties]
    return jsonify(filtered_properties_list), 200

if __name__ == '__main__':
    app.run(debug=True)
