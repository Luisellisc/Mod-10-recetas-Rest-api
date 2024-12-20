from flask import Flask, request, jsonify, flash, redirect, url_for
from flask_pymongo import PyMongo
from flask_mail import Mail, Message
from celery import Celery

app = Flask(__name__)
app.secret_key = "supersecretkey"


app.config['MONGO_URI'] = 'mongodb://localhost:27017/recetario'
mongo = PyMongo(app)
db = mongo.db


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'recetas_flask@gmail.com'
app.config['MAIL_PASSWORD'] = 'celary2004'

mail = Mail(app)


app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task
def enviar_correo_asincrono(asunto, destinatarios, cuerpo):
    with app.app_context():
        msg = Message(asunto, sender=app.config['MAIL_USERNAME'], recipients=destinatarios)
        msg.body = cuerpo
        mail.send(msg)


@app.route('/recetas', methods=['GET'])
def obtener_recetas():
    recetas = db.recetas.find()
    respuesta = []
    for receta in recetas:
        respuesta.append({
            "_id": str(receta["_id"]),
            "nombre": receta["nombre"],
            "ingredientes": receta["ingredientes"],
            "pasos": receta["pasos"]
        })
    return jsonify(respuesta), 200


@app.route('/recetas', methods=['POST'])
def agregar_receta():
    datos = request.json
    if not datos.get('nombre') or not datos.get('ingredientes') or not datos.get('pasos'):
        return jsonify({"error": "Todos los campos son obligatorios"}), 400
    
    receta = {
        "nombre": datos["nombre"],
        "ingredientes": datos["ingredientes"],
        "pasos": datos["pasos"]
    }
    resultado = db.recetas.insert_one(receta)

   
    enviar_correo_asincrono.delay(
        "Nueva receta agregada",
        ["listarecetas@gmail.com"],
        f"Se ha añadido una nueva receta: {datos['nombre']}"
    )

    return jsonify({"mensaje": "Receta agregada", "id": str(resultado.inserted_id)}), 201


@app.route('/recetas/<id>', methods=['PUT'])
def actualizar_receta(id):
    datos = request.json
    receta_actualizada = {}
    if datos.get("nombre"):
        receta_actualizada["nombre"] = datos["nombre"]
    if datos.get("ingredientes"):
        receta_actualizada["ingredientes"] = datos["ingredientes"]
    if datos.get("pasos"):
        receta_actualizada["pasos"] = datos["pasos"]

    resultado = db.recetas.update_one({"_id": ObjectId(id)}, {"$set": receta_actualizada})
    if resultado.matched_count == 0:
        return jsonify({"error": "Receta no encontrada"}), 404

    return jsonify({"mensaje": "Receta actualizada"}), 200


@app.route('/recetas/<id>', methods=['DELETE'])
def eliminar_receta(id):
    resultado = db.recetas.delete_one({"_id": ObjectId(id)})
    if resultado.deleted_count == 0:
        return jsonify({"error": "Receta no encontrada"}), 404

    return jsonify({"mensaje": "Receta eliminada"}), 200

if __name__ == "__main__":
    app.run(debug=True)
