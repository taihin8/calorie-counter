from flask import Blueprint, jsonify
from flask_login import login_required
import speech_recognition as sr

voice_bp = Blueprint('voice', __name__)

@voice_bp.route('/speech_to_text', methods=['POST'])
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