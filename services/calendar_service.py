from datetime import date, datetime

class CalendarService:

    @staticmethod
    def parse_date(date_str):
        """Преобразовать строку в дату"""
        if date_str:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return date.today()
        return date.today()

    @staticmethod
    def get_month_days(year, month):
        """Получить дни месяца для календаря"""
        import calendar
        return calendar.monthcalendar(year, month)

    @staticmethod
    def get_month_name(month, month_names):
        """Получить название месяца"""
        return month_names[month - 1] if 1 <= month <= 12 else month_names[0]