import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # ✅ Nur CPU-Modus erzwingen

import json
import tensorflow as tf
from flask import Flask, request, jsonify

app = Flask(__name__)

# === KI Trainingsstatus ===
TRAINING_STATUS_FILE = "training_status.json"


# === Hilfsfunktionen ===
def save_status(data):
    with open(TRAINING_STATUS_FILE, "w") as f:
        json.dump(data, f)


def load_status():
    if not os.path.exists(TRAINING_STATUS_FILE):
        return {"is_training": False, "message": "❌ Keine Statusdaten gefunden."}
    with open(TRAINING_STATUS_FILE, "r") as f:
        return json.load(f)


# === Dummy KI Trainingsfunktion ===
def train_model():
    status = {"is_training": True, "message": "🚀 Training läuft..."}
    save_status(status)

    try:
        # Beispielmodell (TensorFlow CPU)
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation="relu", input_shape=(10,)),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid")
        ])

        model.compile(optimizer="adam", loss="binary_crossentropy")
        import numpy as np
        x = np.random.random((500, 10))
        y = np.random.randint(2, size=(500, 1))
        model.fit(x, y, epochs=5, verbose=0)

        status = {"is_training": False, "message": "✅ Training erfolgreich abgeschlossen."}
        save_status(status)

    except Exception as e:
        status = {"is_training": False, "message": f"❌ Fehler: {e}"}
        save_status(status)


# === API-Routen ===

@app.route("/")
def index():
    return "✅ Monica Option Training Worker läuft."


@app.route("/start_training", methods=["POST"])
def start_training():
    from threading import Thread
    Thread(target=train_model).start()
    return jsonify({"message": "Training gestartet."})


@app.route("/status", methods=["GET"])
def get_status():
    return jsonify(load_status())


# === Startpoint für Render ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Monica Option KI-Worker läuft auf Port {port}")
    app.run(host="0.0.0.0", port=port)
