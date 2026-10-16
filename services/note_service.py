from models import Note
from extensions import db
from datetime import date

class NoteService:

    @staticmethod
    def get_notes_for_date(user_id, selected_date):
        """Получить все заметки пользователя за указанную дату"""
        return Note.query.filter_by(
            user_id=user_id
        ).filter(
            db.func.date(Note.created_at) == selected_date
        ).order_by(Note.created_at.desc()).all()

    @staticmethod
    def get_notes_for_month(user_id, selected_date):
        """Получить все заметки пользователя за месяц"""
        start_of_month = selected_date.replace(day=1)
        if selected_date.month == 12:
            end_of_month = selected_date.replace(year=selected_date.year + 1, month=1, day=1)
        else:
            end_of_month = selected_date.replace(month=selected_date.month + 1, day=1)

        return Note.query.filter_by(
            user_id=user_id
        ).filter(
            Note.created_at >= start_of_month,
            Note.created_at < end_of_month
        ).all()

    @staticmethod
    def create_note(user_id, content):
        """Создать новую заметку"""
        note = Note(content=content, user_id=user_id)
        db.session.add(note)
        db.session.commit()
        return note

    @staticmethod
    def update_note(note_id, user_id, content):
        """Обновить заметку"""
        note = Note.query.get_or_404(note_id)
        if note.user_id == user_id and content:
            note.content = content
            note.updated_at = db.func.now()
            db.session.commit()
            return True
        return False

    @staticmethod
    def delete_note(note_id, user_id):
        """Удалить заметку"""
        note = Note.query.get_or_404(note_id)
        if note.user_id == user_id:
            db.session.delete(note)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_notes_count_per_day(notes):
        """Преобразовать список заметок в словарь {дата: количество}"""
        from collections import defaultdict
        count = defaultdict(int)
        for note in notes:
            note_date = note.created_at.date().isoformat()
            count[note_date] += 1
        return dict(count)