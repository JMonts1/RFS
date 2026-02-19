import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///marbetes.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Marbete(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(50), unique=True)
    tipo_marbete = db.Column(db.String(100))
    fecha_elaboracion = db.Column(db.String(50))
    marca = db.Column(db.String(200))
    tipo_producto = db.Column(db.String(100))
    alcohol = db.Column(db.String(20))
    capacidad = db.Column(db.String(20))
    origen = db.Column(db.String(200))
    productor = db.Column(db.String(200))
    rfc = db.Column(db.String(50))

with app.app_context():
    db.create_all()

def extraer(texto, campo, ocurrencia=1):
    if campo in texto:
        partes = texto.split(campo)
        if len(partes) > ocurrencia:
            return partes[ocurrencia].split("\n")[0].strip()
        elif len(partes) > 1:
            return partes[1].split("\n")[0].strip()
    return ""

@app.route("/sat", methods=["POST"])
def consultar_sat():
    data = request.get_json()
    qr = data.get("qr")

    if not qr:
        return jsonify({"error": "QR vacío"}), 400

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)

    try:
        driver.get(qr)
        time.sleep(15)  # Esperar a que la página cargue completamente

        texto = driver.execute_script("return document.body.innerText")
        print("TEXTO EXTRAÍDO:", texto)

        resultado = {
            "tipo_marbete": extraer(texto, "Tipo:", 1),
            "folio": extraer(texto, "Folio:", 1),
            "fecha_elaboracion": extraer(texto, "Fecha de elaboración:", 1),
            "marca": extraer(texto, "Nombre o marca:", 1),
            "tipo_producto": extraer(texto, "Tipo:", 2),
            "alcohol": extraer(texto, "Graduación alcohólica:", 1),
            "capacidad": extraer(texto, "Capacidad:", 1),
            "origen": extraer(texto, "Origen del producto", 1),
            "productor": extraer(texto, "Nombre:", 1),
            "rfc": extraer(texto, "RFC:", 1)
        }

        if not resultado["folio"]:
            return jsonify({"error": "MARBETE INVALIDO", "detalle": "No se pudo extraer el folio"}), 422

        existe = Marbete.query.filter_by(folio=resultado["folio"]).first()
        if existe:
            return jsonify({"error": "DUPLICADO", "folio": resultado["folio"]}), 409

        nuevo = Marbete(**resultado)
        db.session.add(nuevo)
        db.session.commit()

        return jsonify(resultado)

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

    finally:
        driver.quit()

@app.route("/registros", methods=["GET"])
def obtener_registros():
    registros = Marbete.query.all()
    data = [{
        "tipo_marbete": r.tipo_marbete,
        "folio": r.folio,
        "fecha_elaboracion": r.fecha_elaboracion,
        "marca": r.marca,
        "tipo_producto": r.tipo_producto,
        "alcohol": r.alcohol,
        "capacidad": r.capacidad,
        "origen": r.origen,
        "productor": r.productor,
        "rfc": r.rfc
    } for r in registros]
    print(f"Registros encontrados: {len(data)}")
    return jsonify(data)

@app.route("/limpiar", methods=["POST"])
def limpiar():
    Marbete.query.delete()
    db.session.commit()
    return jsonify({"mensaje": "Base limpia"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)