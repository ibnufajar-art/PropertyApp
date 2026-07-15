from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import joblib
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

db = mysql.connector.connect(
    host=os.environ.get("MYSQLHOST", "localhost"),
    user=os.environ.get("MYSQLUSER", "root"),
    password=os.environ.get("MYSQLPASSWORD", ""),
    database=os.environ.get("MYSQLDATABASE", "property_app"),
    port=int(os.environ.get("MYSQLPORT", 3306))
)

cursor = db.cursor(dictionary=True)

# LOAD MODEL AI
model = joblib.load("property_model.pkl")

@app.route("/")
def home():
    return jsonify({
        "message": "Backend Property API Running"
    })

@app.route("/stats")
def stats():

    cursor.execute(
        "SELECT COUNT(*) as total_property FROM properties"
    )
    property_count = cursor.fetchone()

    cursor.execute(
        "SELECT COUNT(*) as total_user FROM users"
    )
    user_count = cursor.fetchone()

    cursor.execute(
        "SELECT COUNT(*) as total_favorite FROM favorites"
    )
    favorite_count = cursor.fetchone()

    return jsonify({
        "property": property_count["total_property"],
        "user": user_count["total_user"],
        "favorite": favorite_count["total_favorite"]
    })

# AMBIL SEMUA PROPERTY
@app.route("/properties", methods=["GET"])
def get_properties():

    cursor.execute("""
        SELECT
            properties.*,
            categories.name AS category
        FROM properties
        LEFT JOIN categories
            ON properties.category_id = categories.id
    """)

    data = cursor.fetchall()

    return jsonify(data)

@app.route("/categories")
def get_categories():

    cursor.execute("""
        SELECT *
        FROM categories
        ORDER BY name ASC
    """)

    data = cursor.fetchall()

    return jsonify(data)

@app.route("/properties/<int:id>", methods=["DELETE"])
def delete_property(id):

    cursor.execute(
        "DELETE FROM properties WHERE id=%s",
        (id,)
    )

    db.commit()

    return jsonify({
        "success": True,
        "message": "Property berhasil dihapus"
    })

@app.route("/properties/<int:id>", methods=["PUT"])
def update_property(id):

    data = request.json

    cursor.execute(
        """
        UPDATE properties
        SET
            title=%s,
            location=%s,
            price=%s
        WHERE id=%s
        """,
        (
            data["title"],
            data["location"],
            data["price"],
            id
        )
    )

    db.commit()

    return jsonify({
        "success": True,
        "message": "Property berhasil diupdate"
    })

@app.route("/favorites", methods=["POST"])
def add_favorite():

    data = request.json
    property_id = data.get("property_id")

    cursor.execute(
        "SELECT * FROM favorites WHERE property_id=%s",
        (property_id,)
    )

    existing = cursor.fetchone()

    if existing:
        return jsonify({
            "success": False,
            "message": "Property sudah ada di favorit"
        })

    cursor.execute(
        """
        INSERT INTO favorites(property_id)
        VALUES(%s)
        """,
        (property_id,)
    )

    db.commit()

    return jsonify({
        "success": True,
        "message": "Property berhasil ditambahkan ke favorit"
    })

@app.route("/favorites/<int:property_id>", methods=["DELETE"])
def delete_favorite(property_id):

    cursor.execute(
        "DELETE FROM favorites WHERE property_id=%s",
        (property_id,)
    )

    db.commit()

    return jsonify({
        "success": True,
        "message": "Favorit berhasil dihapus"
    })

@app.route("/favorites", methods=["GET"])
def get_favorites():
        try:

            cursor.execute("""
                SELECT p.*
                FROM favorites f
                JOIN properties p
                ON f.property_id = p.id
                ORDER BY f.id DESC
            """)

            data = cursor.fetchall()

            return jsonify(data)
    
        except Exception as e:
            return jsonify({
            "success": False,
            "message": str(e)
        })

@app.route("/search")
def search_property():

    keyword = request.args.get("keyword", "")

    cursor.execute("""
        SELECT *
        FROM properties
        WHERE title LIKE %s
        OR location LIKE %s
        ORDER BY id DESC
    """, (
        f"%{keyword}%",
        f"%{keyword}%"
    ))

    data = cursor.fetchall()

    print("Hasil Pencarian:", data)

    return jsonify(data)

# TAMBAH PROPERTY
@app.route("/add-property", methods=["POST"])
def add_property():

    data = request.json

    cursor.execute(
        """
        INSERT INTO properties
        (
            title,
            location,
            price,
            bedrooms,
            bathrooms,
            area,
            description,
            image,
            latitude,
            longitude
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data["title"],
            data["location"],
            data["price"],
            data["bedrooms"],
            data["bathrooms"],
            data["area"],
            data["description"],
            data["image"],
            data["latitude"],
            data["longitude"]
        )
    )

    db.commit()

    return jsonify({
        "success": True,
        "message": "Property berhasil ditambahkan"
    })

@app.route("/register", methods=["POST"])
def register():

    data = request.json

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    cursor.execute(
        """
        INSERT INTO users
        (name,email,password)
        VALUES (%s,%s,%s)
        """,
        (name, email, password)
    )

    db.commit()

    return jsonify({
        "success": True,
        "message": "Register berhasil",
        "user": {
            "name": name,
            "email": email
        }
    })

@app.route("/login", methods=["POST"])
def login():
    data = request.json

    email = data.get("email")
    password = data.get("password")

    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, password)
    )

    user = cursor.fetchone()

    if user:
        return jsonify({
            "success": True,
            "message": "Login berhasil",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
        })

    return jsonify({
        "success": False,
        "message": "Email atau password salah"
    }), 401


@app.route("/test")
def test():
    return jsonify({
        "success": True,
        "message": "Backend aktif"
    })

@app.route("/predict", methods=["GET", "POST"])
def predict():

    if request.method == "GET":
        return jsonify({
            "message": "Endpoint Predict Aktif"
        })

    try:
        data = request.json

        luas_bangunan = float(data["luas_bangunan"])
        kamar_tidur = int(data["kamar_tidur"])
        kamar_mandi = int(data["kamar_mandi"])

        input_data = pd.DataFrame(
            [[luas_bangunan, kamar_tidur, kamar_mandi]],
            columns=[
                "luas_bangunan",
                "kamar_tidur",
                "kamar_mandi"
            ]
        )

        hasil = model.predict(input_data)[0]

        return jsonify({
            "success": True,
            "prediksi_harga": int(hasil)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        })

@app.route("/ai-test")
def ai_test():
    return jsonify({
        "success": True,
        "message": "Model AI aktif"
    })

@app.route("/chart-data")
def chart_data():

    cursor.execute("""
        SELECT location, COUNT(*) as total
        FROM properties
        GROUP BY location
    """)

    data = cursor.fetchall()

    labels = []
    values = []

    for item in data:
        labels.append(item["location"])
        values.append(item["total"])

    return jsonify({
        "labels": labels,
        "values": values
    })

@app.route("/analytics")
def analytics():

    cursor.execute("""
        SELECT AVG(price) as avg_price
        FROM properties
    """)

    avg_price = cursor.fetchone()

    return jsonify({
        "avg_price": int(avg_price["avg_price"] or 0)
    })

@app.route("/chat-ai", methods=["POST"])
def chat_ai():

    data = request.json
    message = data.get("message", "").lower()

    if "bandung" in message:
        reply = "Saya menemukan beberapa properti di Bandung."

    elif "jakarta" in message:
        reply = "Saya menemukan beberapa properti di Jakarta."

    elif "villa" in message:
        reply = "Terdapat beberapa villa yang tersedia."

    else:
        reply = "Mohon jelaskan lokasi atau budget yang Anda inginkan."

    return jsonify({
        "reply": reply
    })

@app.route("/recommend", methods=["POST"])
def recommend():

    try:

        data = request.json

        budget = int(data.get("budget", 0))
        bedrooms = int(data.get("bedrooms", 0))

        cursor.execute(
            """
            SELECT *
            FROM properties
            WHERE price <= %s
            AND bedrooms >= %s
            ORDER BY price DESC
            LIMIT 10
            """,
            (budget, bedrooms)
        )

        recommendations = cursor.fetchall()

        return jsonify({
            "success": True,
            "recommendations": recommendations
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        })
    
@app.route("/recommend-budget", methods=["POST"])
def recommend_budget():

    data = request.get_json()

    print("DATA:", data)

    budget = int(data["budget"])

    cursor.execute("""
        SELECT *
        FROM properties
        WHERE price <= %s
        ORDER BY price DESC
        LIMIT 5
    """, (budget,))

    result = cursor.fetchall()

    print("HASIL:", result)

    return jsonify(result)

@app.route("/dashboard", methods=["GET"])
def dashboard():

    try:
        # Total Property
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM properties
        """)
        total_property = cursor.fetchone()["total"]

        # Rata-rata Harga
        cursor.execute("""
            SELECT AVG(price) AS avg_price
            FROM properties
        """)
        avg_price = cursor.fetchone()["avg_price"]

        # Data Grafik
        cursor.execute("""
            SELECT title, price
            FROM properties
            ORDER BY id DESC
            LIMIT 5
        """)
        chart_data = cursor.fetchall()

        return jsonify({
            "success": True,
            "total_property": total_property,
            "avg_price": avg_price,
            "chart_data": chart_data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        })

print(app.url_map)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)