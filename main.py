import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os

USERS_DIR = "users"

def get_user_file(username):
    """Возвращает путь к файлу заметок пользователя"""
    if not os.path.exists(USERS_DIR):
        os.makedirs(USERS_DIR)
    return os.path.join(USERS_DIR, f"{username}.json")

def load_notes(username):
    """Загружает заметки конкретного пользователя"""
    filepath = get_user_file(username)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_notes(username, notes):
    """Сохраняет заметки конкретного пользователя"""
    filepath = get_user_file(username)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

class LoginWindow:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("📓 Вход в ежедневник")
        self.window.geometry("300x200")
        self.window.resizable(False, False)

        tk.Label(self.window, text="Добро пожаловать!", font=("Arial", 16)).pack(pady=10)
        tk.Label(self.window, text="Введите ваше имя пользователя:").pack(pady=5)

        self.username_entry = tk.Entry(self.window, width=30)
        self.username_entry.pack(pady=5)
        self.username_entry.bind("<Return>", lambda e: self.login())

        self.login_btn = tk.Button(self.window, text="🔑 Войти", command=self.login, width=20)
        self.login_btn.pack(pady=10)

        self.new_btn = tk.Button(self.window, text="➕ Новый пользователь", command=self.new_user, width=20)
        self.new_btn.pack(pady=5)

        self.window.mainloop()

    def login(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Ошибка", "Введите имя пользователя")
            return

        # Проверяем, есть ли файл пользователя
        user_file = get_user_file(username)
        if not os.path.exists(user_file):
            # Если пользователь новый — создаём
            save_notes(username, [])
            messagebox.showinfo("Успех", f"Пользователь '{username}' создан!")

        self.window.destroy()
        # Запускаем основное приложение для этого пользователя
        app = NotesApp(username)

    def new_user(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Ошибка", "Введите имя пользователя")
            return

        user_file = get_user_file(username)
        if os.path.exists(user_file):
            messagebox.showwarning("Ошибка", f"Пользователь '{username}' уже существует!")
            return

        save_notes(username, [])
        messagebox.showinfo("Успех", f"Пользователь '{username}' создан! Теперь войдите.")

class NotesApp:
    def __init__(self, username):
        self.username = username
        self.notes = load_notes(username)

        self.root = tk.Tk()
        self.root.title(f"📓 Ежедневник — {username}")
        self.root.geometry("420x550")
        self.root.resizable(False, False)

        # Верхняя панель с именем пользователя и выходом
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, pady=5)

        tk.Label(top_frame, text=f"👤 {username}", font=("Arial", 10), fg="gray").pack(side=tk.LEFT, padx=10)

        logout_btn = tk.Button(top_frame, text="🚪 Выйти", command=self.logout, font=("Arial", 9))
        logout_btn.pack(side=tk.RIGHT, padx=10)

        tk.Label(self.root, text="Введите заметку:", font=("Arial", 12)).pack(pady=5)

        self.entry = tk.Entry(self.root, width=45, font=("Arial", 11))
        self.entry.pack(pady=5)
        self.entry.bind("<Return>", lambda e: self.add_note())

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="➕ Добавить", command=self.add_note, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="❌ Удалить", command=self.delete_note, width=12).pack(side=tk.LEFT, padx=5)

        tk.Button(self.root, text="🗑️ Очистить всё", command=self.clear_all, width=25, fg="red").pack(pady=5)

        tk.Label(self.root, text="--- Ваши заметки ---", font=("Arial", 10)).pack()

        self.listbox = tk.Listbox(self.root, width=50, height=15, font=("Arial", 11))
        self.listbox.pack(pady=5, padx=10)

        self.refresh_list()
        self.root.mainloop()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for note in self.notes:
            self.listbox.insert(tk.END, note)

    def add_note(self):
        note = self.entry.get()
        if note:
            self.notes.append(note)
            save_notes(self.username, self.notes)
            self.refresh_list()
            self.entry.delete(0, tk.END)

    def delete_note(self):
        try:
            index = self.listbox.curselection()[0]
            self.notes.pop(index)
            save_notes(self.username, self.notes)
            self.refresh_list()
        except:
            messagebox.showwarning("Ошибка", "Выберите заметку для удаления")

    def clear_all(self):
        if messagebox.askyesno("Очистка", "Удалить все заметки?"):
            self.notes.clear()
            save_notes(self.username, self.notes)
            self.refresh_list()

    def logout(self):
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            self.root.destroy()
            # Возвращаемся к окну входа
            LoginWindow()

if __name__ == "__main__":
    LoginWindow()