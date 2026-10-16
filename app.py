from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, User, Note
from datetime import datetime, date
import speech_recognition as sr
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# Названия месяцев
MONTH_NAMES = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
               'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

# ============================================================
# 1. СТРАНИЦЫ (маршруты для отображения HTML)
# ============================================================

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        return render_template('login.html', error='Неверное имя пользователя или пароль')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Пользователь уже существует')
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    # Получаем выбранную дату
    selected_date_str = request.args.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()  # <-- ВСЕГДА ТЕКУЩАЯ ДАТА

    collapsed = request.args.get('collapsed', '0')

    # Загружаем заметки за выбранную дату
    notes = Note.query.filter_by(
        user_id=current_user.id
    ).filter(
        db.func.date(Note.created_at) == selected_date
    ).order_by(Note.created_at.desc()).all()

    # Считаем заметки для каждого дня месяца
    start_of_month = selected_date.replace(day=1)
    if selected_date.month == 12:
        end_of_month = selected_date.replace(year=selected_date.year + 1, month=1, day=1)
    else:
        end_of_month = selected_date.replace(month=selected_date.month + 1, day=1)

    all_notes_month = Note.query.filter_by(
        user_id=current_user.id
    ).filter(
        Note.created_at >= start_of_month,
        Note.created_at < end_of_month
    ).all()

    notes_count = {}
    for note in all_notes_month:
        note_date = note.created_at.date().isoformat()
        notes_count[note_date] = notes_count.get(note_date, 0) + 1

    notes_data_json = json.dumps(notes_count)

    return render_template(
        'index.html',
        notes=notes,
        username=current_user.username,
        selected_date=selected_date,
        today=date.today(),
        month_names=MONTH_NAMES,
        notes_data=notes_data_json,
        collapsed=collapsed  # <-- ПЕРЕДАЁМ ПАРАМЕТР В ШАБЛОН
    )
# ============================================================
# 2. ОБЫЧНЫЕ (синхронные) МАРШРУТЫ ДЛЯ ФОРМ
# ============================================================

@app.route('/add_note', methods=['POST'])
@login_required
def add_note():
    content = request.form.get('content')
    if content:
        note = Note(content=content, user_id=current_user.id)
        db.session.add(note)
        db.session.commit()

    selected_date = request.form.get('date')
    if selected_date:
        return redirect(url_for('index', date=selected_date))
    return redirect(url_for('index'))

@app.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()

    selected_date = request.form.get('date')
    if selected_date:
        return redirect(url_for('index', date=selected_date))
    return redirect(url_for('index'))

@app.route('/edit_note/<int:note_id>', methods=['POST'])
@login_required
def edit_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id == current_user.id:
        content = request.form.get('content')
        if content:
            note.content = content
            note.updated_at = db.func.now()
            db.session.commit()

    selected_date = request.form.get('date')
    if selected_date:
        return redirect(url_for('index', date=selected_date))
    return redirect(url_for('index'))

# ============================================================
# 3. AJAX-МАРШРУТЫ (без перезагрузки страницы)
# ============================================================

@app.route('/add_note_ajax', methods=['POST'])
@login_required
def add_note_ajax():
    data = request.get_json()
    content = data.get('content')
    date_str = data.get('date')

    if content:
        note = Note(content=content, user_id=current_user.id)
        db.session.add(note)
        db.session.commit()

        return jsonify({
            'success': True,
            'note': {
                'id': note.id,
                'content': note.content,
                'created_at': note.created_at.isoformat()
            }
        })
    return jsonify({'success': False, 'error': 'Empty content'})

@app.route('/edit_note_ajax/<int:note_id>', methods=['POST'])
@login_required
def edit_note_ajax(note_id):
    data = request.get_json()
    content = data.get('content')

    note = Note.query.get_or_404(note_id)
    if note.user_id == current_user.id and content:
        note.content = content
        note.updated_at = db.func.now()
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/delete_note_ajax/<int:note_id>', methods=['POST'])
@login_required
def delete_note_ajax(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

# ============================================================
# 4. ГОЛОСОВОЙ ВВОД
# ============================================================

@app.route('/speech_to_text', methods=['POST'])
@login_required
def speech_to_text():
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            text = recognizer.recognize_google(audio, language='ru-RU')
            return jsonify({'success': True, 'text': text})
    except sr.WaitTimeoutError:
        return jsonify({'success': False, 'error': '⏱️ Ничего не услышал'})
    except sr.UnknownValueError:
        return jsonify({'success': False, 'error': '🤔 Не разобрал'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================================
# 5. ВЫХОД
# ============================================================

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ============================================================
# 6. ЗАПУСК
# ============================================================
@app.route('/get_notes_ajax', methods=['GET'])
@login_required
def get_notes_ajax():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'success': False, 'error': 'No date provided'})

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'})

    notes = Note.query.filter_by(
        user_id=current_user.id
    ).filter(
        db.func.date(Note.created_at) == selected_date
    ).order_by(Note.created_at.desc()).all()

    notes_data = []
    for note in notes:
        notes_data.append({
            'id': note.id,
            'content': note.content,
            'created_at': note.created_at.isoformat(),
            'updated_at': note.updated_at.isoformat() if note.updated_at else note.created_at.isoformat()
        })

    return jsonify({
        'success': True,
        'notes': notes_data,
        'count': len(notes_data)
    })
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)