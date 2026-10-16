from flask import Blueprint, redirect, url_for

# Создаём главный блюпринт
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return redirect(url_for('auth.login'))

def register_blueprints(app):
    """Регистрация всех блюпринтов"""
    from routes.auth import auth_bp
    from routes.notes import notes_bp
    from routes.voice import voice_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(notes_bp, url_prefix='/notes')
    app.register_blueprint(voice_bp, url_prefix='/voice')