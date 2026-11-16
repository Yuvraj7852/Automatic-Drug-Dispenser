from flask import Flask, render_template
from flask_login import current_user
from .config import Config
from .extensions import db, login_manager, migrate, csrf, limiter

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from .blueprints.auth import auth_bp
    from .blueprints.doctor import doctor_bp
    from .blueprints.patient import patient_bp
    from .blueprints.pharmacy import pharmacy_bp
    from .blueprints.admin import admin_bp
    from .blueprints.orders import orders_bp
    from .blueprints.dashboard import dashboard_bp
    for blueprint in (auth_bp, doctor_bp, patient_bp, pharmacy_bp, admin_bp, orders_bp, dashboard_bp):
        app.register_blueprint(blueprint)

    @app.context_processor
    def inject_helpers():
        from datetime import datetime
        return {"logged_in_user": current_user, "now": datetime.utcnow}

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    return app
