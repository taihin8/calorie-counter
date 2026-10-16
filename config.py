import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///journal.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Названия месяцев
    MONTH_NAMES = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']