from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager

from .database import User, init_db


login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-this-secret-in-production"
    app.config["UPLOAD_FOLDER"] = "uploads"
    CORS(app)

    login_manager.init_app(app)
    login_manager.login_view = "routes.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(int(user_id))

    init_db()

    from .api.routes import bp

    app.register_blueprint(bp)
    return app
