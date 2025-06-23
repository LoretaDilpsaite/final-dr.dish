from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
import time


# --- OAuth Imports ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from oauth.models import Base as OAuthBase, OAuth2Client
from oauth.server import create_authorization_server
from oauth.routes import register_oauth_routes
from cryptography.fernet import Fernet

# --- App + DB ---
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///insulin_data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "REPLACE_ME"

# Insulin  DB
db = SQLAlchemy(app)

# OAuth-spezifische DB-connection
oauth_engine = create_engine("sqlite:///auth.db")
OAuthSession = sessionmaker(bind=oauth_engine)
oauth_session = OAuthSession()

# create table
with app.app_context():
    db.create_all()
OAuthBase.metadata.create_all(oauth_engine)

# create AuthorizationServer
auth_server = create_authorization_server(
    app,
    oauth_session,
    query_client=lambda cid: oauth_session.query(OAuth2Client).filter_by(client_id=cid).first()
)

# register OAuth2-Route
register_oauth_routes(app, auth_server, oauth_session)

# --- FHIR Server ---
PATIENT_ID = "A16151615"
INSULIN_SCHEMA_URL = "https://hapi.fhir.org/baseR4/MedicationDispense/M14131413"
FHIR_BASE_URL = "https://hapi.fhir.org/baseR4"

# --- Insulin-Modell ---
class InsulinData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.String(20), nullable=False)
    bloodglucose = db.Column(db.Float, nullable=False)
    carbohydrateexchange = db.Column(db.Float, nullable=False)
    insulinamount = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "patient_id": self.patient_id,
            "bloodglucose": self.bloodglucose,
            "carbohydrateexchange": self.carbohydrateexchange,
            "insulinamount": self.insulinamount
        }

# --- Function for Insulin-Calculation ---
def load_insulinschema():
    response = requests.get(INSULIN_SCHEMA_URL)
    response.raise_for_status()
    data = response.json()
    corr_table = []
    for ext in data.get("extension", []):
        if ext.get("url") == "http://example.org/fhir/StructureDefinition/insulin-dosage-schema":
            for range_block in ext.get("extension", []):
                if range_block.get("url") == "range":
                    low = high = dose = None
                    for detail in range_block.get("extension", []):
                        if detail["url"] == "low":
                            low = detail.get("valueInteger")
                        elif detail["url"] == "high":
                            high = detail.get("valueInteger")
                        elif detail["url"] == "dose":
                            try:
                                dose = float(detail.get("valueString", "0 IE").split()[0])
                            except:
                                dose = 0
                    if None not in (low, high, dose):
                        corr_table.append({
                            "low": low,
                            "high": high,
                            "dose": dose
                        })
    return corr_table

def calculate_insulin(bloodglucose, carbohydrateexchange, corr_table):
    correction_insulin = 0
    for input in corr_table:
        if input["low"] <= bloodglucose <= input["high"]:
            correction_insulin = input["dose"]
            break
    meal_insulin = carbohydrateexchange / 2
    total_insulin = correction_insulin + meal_insulin
    return round(total_insulin, 2), round(correction_insulin, 2), round(meal_insulin, 2)

def build_medication_administration(patient_id, insulinamount):
    return {
        "resourceType": "MedicationAdministration",
        "id": f"admin-M14131413",
        "status": "completed",
        "medicationReference": {
            "reference": "MedicationDispense/M14131413"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": datetime.utcnow().isoformat(),
        "dosage": {
            "text": f"{insulinamount} IU Insulin",
            "dose": {
                "value": insulinamount,
                "unit": "IU",
                "system": "http://unitsofmeasure.org",
                "code": "IU"
            }
        }
    }

def send_medication_administration(resource):
    url = f"{FHIR_BASE_URL}/MedicationAdministration/admin-M14131413"
    headers = {"Content-Type": "application/fhir+json"}
    response = requests.put(url, json=resource, headers=headers)
    response.raise_for_status()
    return response.json()

# --- Route ---
@app.route("/")
def index():
    return render_template("index.html", patient_id=PATIENT_ID)

@app.route("/calculate_insulin", methods=["POST"])
def route_berechne_insulin():
    try:
        bloodglucose = float(request.form["bloodglucose"])
        carbohydrateexchange = float(request.form["carbohydrateexchange"])

        corr_table = load_insulinschema()
        total_insulin, correction_insulin, meal_insulin = calculate_insulin(
            bloodglucose, carbohydrateexchange, corr_table
        )

        # save database
        input = InsulinData(
            patient_id=PATIENT_ID,
            bloodglucose=bloodglucose,
            carbohydrateexchange=carbohydrateexchange,
            insulinamount=total_insulin
        )
        db.session.add(input)
        db.session.commit()

        # send FHIR Resource
        med_admin = build_medication_administration(PATIENT_ID, total_insulin)
        fhir_response = send_medication_administration(med_admin)

        return jsonify({
            "patient_id": PATIENT_ID,
            "bloodglucose": bloodglucose,
            "carbohydrateexchange": carbohydrateexchange,
            "total_insulin": total_insulin,
            "correction_insulin": correction_insulin,
            "meal_insulin": meal_insulin,
            "timestamp": input.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "fhir_response": fhir_response,
            "medication_administration": med_admin
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- Main ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

