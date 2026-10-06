from flask import Flask, jsonify
from .config import Config


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    from .auth import configure_auth
    configure_auth(app)

    from .routes.main import bp as main_bp
    from .routes.media import bp as media_bp
    from .routes.transcribe import bp as transcribe_bp
    from .routes.content import bp as content_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(transcribe_bp)
    app.register_blueprint(content_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Resursa nu a fost găsită."), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify(error="Metodă HTTP nepermisă."), 405

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify(error="A apărut o eroare internă."), 500

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="Fișierul sau cererea depășește limita permisă."), 413

    return app
