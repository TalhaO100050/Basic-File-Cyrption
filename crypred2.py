import base64
import os
import sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend

import customtkinter as ctk
from tkinter import messagebox

# --- ŞİFRELEME FONKSİYONLARI ---

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=300_000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_bytes(data: bytes, password: str) -> bytes:
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data)
    return salt + encrypted

def decrypt_bytes(encrypted_data: bytes, password: str) -> bytes:
    salt = encrypted_data[:16]
    encrypted = encrypted_data[16:]
    key = _derive_key(password, salt)
    fernet = Fernet(key)
    return fernet.decrypt(encrypted)

# --- ARAYÜZ (GUI) TASARIMI ---

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LocalFolderEncryptorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Klasör İçi Dosya Şifreleyici")
        self.geometry("600x550")
        self.resizable(False, False)

        # Çalıştığı dizini tespit et (.exe ve .py uyumlu)
        if getattr(sys, 'frozen', False):
            self.current_dir = os.path.dirname(sys.executable)
        else:
            self.current_dir = os.path.dirname(os.path.abspath(__file__))

        self.selected_file = None
        self.radio_var = ctk.StringVar(value="")

        # --- ÜST BAŞLIK VE YENİLE BUTONU ---
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.pack(fill="x", padx=20, pady=10)

        self.lbl_path = ctk.CTkLabel(
            self.frame_top, 
            text=f"📁 Çalışma Alanı: {os.path.basename(self.current_dir)}", 
            font=("Arial", 14, "bold")
        )
        self.lbl_path.pack(side="left")

        self.btn_refresh = ctk.CTkButton(
            self.frame_top, 
            text="🔄 Listeyi Yenile", 
            width=110, 
            command=self.refresh_file_list
        )
        self.btn_refresh.pack(side="right")

        # --- DOSYA LİSTESİ ---
        self.lbl_info = ctk.CTkLabel(self, text="Şifrelenecek veya çözülecek dosyayı seçin:", text_color="gray")
        self.lbl_info.pack(anchor="w", padx=25, pady=(5, 0))

        self.scroll_frame = ctk.CTkScrollableFrame(self, height=220, label_text="Klasördeki Dosyalar")
        self.scroll_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # --- ŞİFRE GİRİŞİ ---
        self.entry_pwd = ctk.CTkEntry(self, placeholder_text="Şifre Giriniz", show="*", width=350)
        self.entry_pwd.pack(pady=15)

        # --- İŞLEM BUTONLARI ---
        self.frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actions.pack(pady=10)

        self.btn_encrypt = ctk.CTkButton(
            self.frame_actions, 
            text="🔒 Seçileni Şifrele", 
            fg_color="#2FA572", 
            hover_color="#1E6B49", 
            width=160,
            command=self.encrypt_action
        )
        self.btn_encrypt.grid(row=0, column=0, padx=10)

        self.btn_decrypt = ctk.CTkButton(
            self.frame_actions, 
            text="🔓 Şifreyi Çöz", 
            fg_color="#E74C3C", 
            hover_color="#962D22", 
            width=160,
            command=self.decrypt_action
        )
        self.btn_decrypt.grid(row=0, column=1, padx=10)

        self.refresh_file_list()

    def refresh_file_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.radio_var.set("")
        self.selected_file = None

        try:
            all_items = os.listdir(self.current_dir)
            files = []

            # Kendisini ve sistem dosyalarını korumak için gizleme
            ignored_extensions = ('.exe', '.py', '.spec', '.bat', '.cmd')

            for item in all_items:
                full_path = os.path.join(self.current_dir, item)
                if os.path.isfile(full_path):
                    if not item.endswith(ignored_extensions):
                        files.append(item)

            if not files:
                lbl_empty = ctk.CTkLabel(self.scroll_frame, text="Bu klasörde işlenebilecek dosya bulunamadı.", text_color="gray")
                lbl_empty.pack(pady=20)
                return

            for file_name in files:
                display_text = f"🔒 {file_name}" if file_name.endswith('.enc') else f"📄 {file_name}"
                
                rb = ctk.CTkRadioButton(
                    self.scroll_frame, 
                    text=display_text, 
                    value=file_name, 
                    variable=self.radio_var,
                    command=self.on_file_select
                )
                rb.pack(anchor="w", pady=5, padx=10)

        except Exception as e:
            messagebox.showerror("Hata", f"Klasör taranırken hata oluştu:\n{e}")

    def on_file_select(self):
        self.selected_file = self.radio_var.get()

    def encrypt_action(self):
        filename = self.selected_file
        password = self.entry_pwd.get()

        if not filename or not password:
            messagebox.showwarning("Eksik Bilgi", "Lütfen listeden bir dosya seçin ve şifre girin.")
            return

        if filename.endswith('.enc'):
            messagebox.showwarning("Uyarı", "Bu dosya zaten şifrelenmiş görünüyor (.enc uzantılı).")
            return

        file_path = os.path.join(self.current_dir, filename)

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            encrypted_data = encrypt_bytes(data, password)

            new_filename = filename + ".enc"
            new_file_path = os.path.join(self.current_dir, new_filename)

            # 1. Yeni şifrelenmiş dosyayı disk üzerine yazıyoruz
            with open(new_file_path, "wb") as f:
                f.write(encrypted_data)

            # 2. Şifreleme ve yazma BAŞARILI olduysa eski orijinal dosyayı siliyoruz
            os.remove(file_path)

            messagebox.showinfo("Başarılı", f"Dosya şifrelendi ve orijinali silindi:\n{new_filename}")
            self.entry_pwd.delete(0, 'end')
            self.refresh_file_list()

        except Exception as e:
            messagebox.showerror("Hata", f"Şifreleme sırasında hata oluştu (Eski dosya korundu):\n{e}")

    def decrypt_action(self):
        filename = self.selected_file
        password = self.entry_pwd.get()

        if not filename or not password:
            messagebox.showwarning("Eksik Bilgi", "Lütfen listeden şifreli bir dosya seçin ve şifre girin.")
            return

        file_path = os.path.join(self.current_dir, filename)

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            decrypted_data = decrypt_bytes(data, password)

            if filename.endswith('.enc'):
                new_filename = filename[:-4]
            else:
                new_filename = "cozulmus_" + filename

            new_file_path = os.path.join(self.current_dir, new_filename)

            # 1. Yeni çözülmüş dosyayı yazıyoruz
            with open(new_file_path, "wb") as f:
                f.write(decrypted_data)

            # 2. Şifre çözme ve yazma BAŞARILI olduysa eski .enc uzantılı dosyayı siliyoruz
            os.remove(file_path)

            messagebox.showinfo("Başarılı", f"Dosya şifresi çözüldü ve şifreli dosya silindi:\n{new_filename}")
            self.entry_pwd.delete(0, 'end')
            self.refresh_file_list()

        except Exception:
            messagebox.showerror("Hata", "Şifre yanlış veya dosya bozuk!\nİşlem iptal edildi, eski dosya silinmedi.")

if __name__ == "__main__":
    app = LocalFolderEncryptorApp()
    app.mainloop()