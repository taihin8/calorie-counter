from flask import Blueprint, render_template, request, jsonify, redirect
from flask_login import login_required, current_user
from datetime import date, datetime
from services.note_service import NoteService
from services.calendar_service import CalendarService
from config import Config
import json

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/index')
@login_required
def index():
    # Получаем дату
    selected_date_str = request.args.get('date')
    selected_date = CalendarService.parse_date(selected_date_str)

    # Получаем параметр collapsed
    collapsed = request.args.get('collapsed', '0')

    # Получаем заметки за день
    notes = NoteService.get_notes_for_date(current_user.id, selected_date)

    # Получаем заметки за месяц для точек в календаре
    month_notes = NoteService.get_notes_for_month(current_user.id, selected_date)
    notes_count = NoteService.get_notes_count_per_day(month_notes)
    notes_data_json = json.dumps(notes_count)

    return render_template(
        'index.html',
        notes=notes,
        username=current_user.username,
        selected_date=selected_date,
        today=date.today(),
        month_names=Config.MONTH_NAMES,
        notes_data=notes_data_json,
        collapsed=collapsed
    )

@notes_bp.route('/add_note_ajax', methods=['POST'])
@login_required
def add_note_ajax():
    data = request.get_json()
    content = data.get('content')

    if content:
        note = NoteService.create_note(current_user.id, content)
        return jsonify({
            'success': True,
            'note': {
                'id': note.id,
                'content': note.content,
                'created_at': note.created_at.isoformat()
            }
        })
    return jsonify({'success': False, 'error': 'Empty content'})

@notes_bp.route('/edit_note_ajax/<int:note_id>', methods=['POST'])
@login_required
def edit_note_ajax(note_id):
    data = request.get_json()
    content = data.get('content')

    success = NoteService.update_note(note_id, current_user.id, content)
    return jsonify({'success': success})

@notes_bp.route('/delete_note_ajax/<int:note_id>', methods=['POST'])
@login_required
def delete_note_ajax(note_id):
    success = NoteService.delete_note(note_id, current_user.id)
    return jsonify({'success': success})

@notes_bp.route('/get_notes_ajax', methods=['GET'])
@login_required
def get_notes_ajax():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'success': False, 'error': 'No date provided'})

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'})

    notes = NoteService.get_notes_for_date(current_user.id, selected_date)

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

# ===== Обычные маршруты (для обратной совместимости) =====

@notes_bp.route('/add_note', methods=['POST'])
@login_required
def add_note():
    content = request.form.get('content')
    if content:
        NoteService.create_note(current_user.id, content)
    return redirect(request.referrer or '/index')

@notes_bp.route('/edit_note/<int:note_id>', methods=['POST'])
@login_required
def edit_note(note_id):
    content = request.form.get('content')
    NoteService.update_note(note_id, current_user.id, content)
    return redirect(request.referrer or '/index')

@notes_bp.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    NoteService.delete_note(note_id, current_user.id)
    return redirect(request.referrer or '/index')