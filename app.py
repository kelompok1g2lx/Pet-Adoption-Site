import os
from os.path import join, dirname
from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, url_for,jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from bson import ObjectId
import jwt
import hashlib


dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")
SECRET_KEY = os.environ.get("SECRET_KEY")

client = MongoClient(MONGODB_URI)

db = client[DB_NAME]

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["UPLOAD_FOLDER"] = "./static/profile_pics"
app.config['UPLOAD_FOLDER_ANIMALS'] = "./static/animal_pics"
UPLOAD_FOLDER_ANIMALS = os.path.join(app.root_path, 'static', 'animal_pics')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


# -------------LOGIN PAGE------------------
@app.route("/login")
def login():
    msg = request.args.get("msg")
    return render_template("login.html", msg=msg)

@app.route('/', methods=['GET', 'POST'])
def home():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})

        return render_template("adopter/adopsi.html", user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))


@app.route("/user/<username>")
def user(username):
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        status = username == payload["id"]  

        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template("user.html", user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.users.find_one(
    {
        "username": username_receive,
        "password": pw_hash,
    })

    if result:
        payload = {
            "id": username_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return redirect(url_for("login", msg="There was a problem logging you in"))


@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    asal_receive = request.form['asal_give']
    kontak_receive = request.form['kontak_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,
        "password": password_hash,
        "profile_name": username_receive,
        "profile_pic": "",
        "profile_pic_real": "profile_pics/profile_placeholder.png",
        "profile_info": "",
        "profile_asal": asal_receive,
        "profile_kontak": kontak_receive,
        "mode" : 'adopter'
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    asal_receive = request.form["asal_give"]
    kontak_receive = request.form["kontak_give"]
    exists = bool(db.user.find_one({"username": username_receive, "profile_asal": asal_receive, "profile_kontak": kontak_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route("/update_profile", methods=["POST"])
def save_img():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        name_receive = request.form["name_give"]
        asal_receive = request.form.get("asal_give")
        kontak_receive = request.form.get("kontak_give")
        print(asal_receive, kontak_receive)
        new_doc = {"profile_name": name_receive, "profile_asal": asal_receive, "profile_kontak": kontak_receive}
        if "file_give" in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"profile_pics/{username}.{extension}"
            file.save("./static/" + file_path)
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path
        db.users.update_one(
            {"username": username},
            {"$set": new_doc}
        )
        return jsonify({"result": "success", "msg": "Profile updated!"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))



# -------------------- BAGIAN 1 ADOPTER
# --------------- ADOPT PAGE ---------------


@app.route('/adopsi')
def adopsi():
    pets = db.pets.find()
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})

        db.users.update_one({'_id' : user_info['_id']}, {'$set' : {'mode' : 'adopter'}})
        return render_template('adopter/adopsi.html', pets=pets, user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    

# @app.route('/delete-pet/<id_pemilik>')
# def delete_pet(id_pemilik):
#     db.pets.delete_one({'id_pemilik': ObjectId(id_pemilik)})
#     return redirect(url_for('adopsi'))

# -------------- SPECIFIED ---------------
@app.route('/species')
def species():
    species = request.args.get('species')
    pets = db.pets.find({'spesies': species})
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        if species == 'cat':
            return render_template('adopter/cat.html', pets=pets, user_info=user_info)
        elif species == 'dog':
            return render_template('adopter/dog.html', pets=pets, user_info=user_info)
        elif species == 'rabbit':
            return render_template('adopter/rabbit.html', pets=pets, user_info=user_info)
        elif species == 'hamster':
            return render_template('adopter/hamster.html', pets=pets, user_info=user_info)
        else:
            
            return redirect(url_for('adopsi'))
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
   
    
@app.route('/cat')
def cat():
    pets = list(db.pets.find({'spesies': 'cat'}))
    for pet in pets:
        pet['_id'] = str(pet['_id'])
        pet['id_pemilik'] = str(pet['id_pemilik'])

    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    return render_template('adopter/cat.html', pets=pets, user_info=user_info)

@app.route('/dog')
def dog():
    pets = list(db.pets.find({'spesies': 'dog'}))
    for pet in pets:
        pet['_id'] = str(pet['_id'])
        pet['id_pemilik'] = str(pet['id_pemilik'])

    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    return render_template('adopter/dog.html', pets=pets, user_info=user_info)

@app.route('/hamster')
def hamster():
    pets = list(db.pets.find({'spesies': 'hamster'}))
    for pet in pets:
        pet['_id'] = str(pet['_id'])
        pet['id_pemilik'] = str(pet['id_pemilik'])
                                
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    return render_template('adopter/hamster.html', pets=pets, user_info=user_info)

@app.route('/rabbit')
def rabbit():
    pets = list(db.pets.find({'spesies': 'rabbit'}))
    for pet in pets:
        pet['_id'] = str(pet['_id'])
        pet['id_pemilik'] = str(pet['id_pemilik'])

    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    return render_template('adopter/rabbit.html', pets=pets, user_info=user_info)




# -------------------- BAGIAN 2 UPLOADER
# -------------- OPEN ADOPTION PAGE -----------------
@app.route('/mypets')
def mypets():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        pets = db.pets.find(
            {
                "id_pemilik": user_info["_id"],
                "status": False  # Filter out adopted pets
            }
        )
        print(pets)

        db.users.update_one({'_id' : user_info['_id']}, {'$set' : {'mode' : 'uploader'}})

        return render_template('uploader/mypets.html', pets=pets, user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    
@app.route('/delete/<pet_id>')
def delete_pet(pet_id):
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        
        # Check if the pet belongs to the current user
        pet = db.pets.find_one({"_id": ObjectId(pet_id), "id_pemilik": user_info["_id"], "status": False})
        if pet:
            db.pets.delete_one({"_id": ObjectId(pet_id)})
        
        return redirect(url_for('mypets'))
    
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


# @app.route('/delete/<pet_id>')
# def delete(id_pemilik):
#     db.pets.delete_one({'id_pemilik': ObjectId(_id)})
#     return redirect(url_for('mypets'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/buka_adopsi', methods=['GET', 'POST'])
def buka_adopsi():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        if request.method == 'POST':
            id_pemilik = user_info['_id']
            kontak = user_info['profile_kontak']
            kota = user_info['profile_asal']
            spesies = request.form['spesies']
            nh = request.form['nh']
            gender = request.form['gender']
            keterangan = request.form['keterangan']
            usia = request.form['usia']
            image = request.files['image']
            status = False  

            if image and allowed_file(image.filename):  
                filename = secure_filename(image.filename)  
                animal_pics = os.path.join(app.config['UPLOAD_FOLDER_ANIMALS'], filename)
                image.save(animal_pics)  
                db.pets.insert_one({
                    'id_pemilik': id_pemilik,
                    'kontak': kontak,
                    'kota': kota,
                    'spesies': spesies,
                    'image': animal_pics,  
                    'nh': nh,
                    'gender': gender,
                    'keterangan': keterangan,
                    'usia': usia,
                    'username': user_info['username'],
                    'status': status
                })
            else:
                
                db.pets.insert_one({
                    'id_pemilik': id_pemilik,
                    'kontak': kontak,
                    'kota': kota,
                    'spesies': spesies,
                    'nh': nh,
                    'gender': gender,
                    'keterangan': keterangan,
                    'usia': usia,
                    'username': user_info['username'],
                    'status': status
                })

            if spesies == 'cat':
                return redirect(url_for('species', species='cat'))
            elif spesies == 'dog':
                return redirect(url_for('species', species='dog'))
            elif spesies == 'rabbit':
                return redirect(url_for('species', species='rabbit'))
            elif spesies == 'hamster':
                return redirect(url_for('species', species='hamster'))
        return render_template('uploader/buka_adopsi.html', user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    

@app.route('/edit/<pet_id>', methods=['GET'])
def edit_pet(pet_id):
    pet = db.pets.find_one({'_id': ObjectId(pet_id)})
    return render_template('uploader/edit_adopsi.html', pet=pet)

@app.route('/update/<pet_id>', methods=['POST'])
def update_pet(pet_id):
    updated_data = {
        'nh': request.form['nh'],
        'keterangan': request.form['keterangan'],
        'gender': request.form['gender'],
        'usia': request.form['usia'],
        'spesies': request.form['spesies'],
        'np': request.form['np'],
        'kontak': request.form['kontak'],
        'kota': request.form['kota']
    }
    result = db.pets.update_one({'_id': ObjectId(pet_id)}, {'$set': updated_data})
    if result.modified_count > 0:
        return redirect('/mypets')
    else:
        return 'Failed to update pet data'
    

@app.route('/send_adoption_request', methods=['POST'])
def send_adoption_request():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        pet_id = ObjectId(request.json['pet_id'])
        id_pemilik = ObjectId(request.json['id_pemilik'])

        user_info = db.users.find_one({"username": payload['id']})

        request_list_owner = list(db.request_list.find(
            {
            'pet_id': pet_id,
            'requesting_id': user_info['_id'],
            'id_pemilik': id_pemilik
            }
        ))

        if len(request_list_owner) >= 1:
            return jsonify({'message': "udah request"})
            
        request_list = {
            'pet_id': pet_id,
            'requesting_id': user_info['_id'],
            'id_pemilik': id_pemilik,
            'status': 'pending'
        }

        db.request_list.insert_one(request_list)

        return jsonify({'message': 'Your adoption request has been sent to the pet owner.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return jsonify({'error': 'Invalid token'})


@app.route('/status1')
def notifications():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        request_list = list(db.request_list.find({'requesting_id': user_info['_id'], 'status': 'pending'}))

        for r in request_list:
            pet = db.pets.find_one({'_id': r['pet_id']})
            pemilik = db.users.find_one({'_id': r['id_pemilik']})
            r['pet'] = pet
            r['pemilik'] = pemilik
        print(request_list)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    return render_template('adopter/status.html', request_list=request_list, user_info=user_info)
    
@app.route('/cancel_request', methods=['POST'])
def cancel_request():
    request_id = ObjectId(request.form['request_id'])
    db.request_list.delete_one({'_id': request_id})
    return redirect(url_for('notifications'))

@app.route('/status2')
def status2():
    pets = db.pets.find()
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        request_list = list(db.request_list.find({'id_pemilik': user_info["_id"], 'status': 'pending'}))
        
        for r in request_list:
            pet = db.pets.find_one({'_id': r['pet_id']})
            calon = db.users.find_one({'_id': r['requesting_id']})
            r['pet'] = pet
            r['calon'] = calon
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    return render_template('uploader/status.html', pets=pets, user_info=user_info, request_list=request_list)


# ----------------- APPROVAL SYSTEM -----------------
@app.route('/approve_request', methods=['POST'])
def approve_request():
    request_id = ObjectId(request.form['request_id'])
    pet_id = ObjectId(request.form['pet_id'])
    db.request_list.update_one({'_id': request_id}, {'$set': {'status': 'approved'}})
    db.pets.update_one({'_id': pet_id}, {'$set': {'status': True}})
    return redirect(url_for('status2'))

@app.route('/decline_request', methods=['POST'])
def decline_request():
    request_id = ObjectId(request.form['request_id'])
    db.request_list.update_one({'_id': request_id}, {'$set': {'status': 'declined'}})
    return redirect(url_for('status2'))


# ---------------- HISTORY PAGE -------------------


@app.route('/history1')
def history1():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        adopted_pets = list(db.request_list.find({'requesting_id': user_info['_id'], 'status': {'$ne': 'pending'}}))
        for p in adopted_pets:
            pet = db.pets.find_one({'_id': p['pet_id']})
            pemilik = db.users.find_one({'_id': p['id_pemilik']})
            p['pemilik'] = pemilik          
            p['pet'] = pet

        adopted_pets = [x for x in adopted_pets if not (x['pet'] == None)]
        return render_template('adopter/history.html', adopted_pets=adopted_pets, user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/history2')
def history2():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        adopted_pets = list(db.request_list.find({'id_pemilik': user_info['_id'], 'status': {'$ne': 'pending'}}))
        for a in adopted_pets:
            pet = db.pets.find_one({'_id': a['pet_id']})
            calon = db.users.find_one({'_id': a['requesting_id']})
            a['pet'] = pet
            a['calon'] = calon
        
        adopted_pets = [i for i in adopted_pets if not (i['pet'] == None)]
        return render_template('uploader/history.html', adopted_pets=adopted_pets, user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
        


  






    

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)






    