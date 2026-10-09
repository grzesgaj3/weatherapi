from flask import Flask, jsonify
from config import Config
from models import db
from routes.measurements import bp as measurements_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    app.register_blueprint(measurements_bp)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(404)
    def not_found(_):
        return jsonify(error="Nie znaleziono zasobu"), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify(error="Metoda niedozwolona"), 405

    @app.errorhandler(500)
    def internal(_):
        return jsonify(error="Błąd serwera"), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)