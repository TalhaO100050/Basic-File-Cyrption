import base64
import os
import sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend

import customtkinter as ctk

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

def handle_conflict_and_get_path(directory: str, filename: str) -> str:
    target_path = os.path.join(directory, filename)
    
    if not os.path.exists(target_path):
        return target_path
        
    sub_dir = os.path.join(directory, "Arşiv")
    os.makedirs(sub_dir, exist_ok=True)
    
    if filename.endswith('.enc'):
        name_part = filename[:-4]
        ext = '.enc'
    else:
        name_part, ext = os.path.splitext(filename)
        
    counter = 1
    while True:
        new_name = f"{name_part}_{counter}{ext}"
        backup_path = os.path.join(sub_dir, new_name)
        if not os.path.exists(backup_path):
            break
        counter += 1
        
    try:
        os.replace(target_path, backup_path)
    except Exception as e:
        raise Exception(f"Eski dosya Arşiv'e taşınırken hata oluştu:\n{e}")
        
    return target_path


# --- ÖZEL MESAJ PENCERESİ ---

class CustomMessageBox(ctk.CTkToplevel):
    def __init__(self, master, title="Mesaj", message="", msg_type="info"):
        super().__init__(master)
        self.title(title)
        self.geometry("450x220")
        self.resizable(False, False)
        
        self.transient(master)
        self.grab_set()
        
        colors = {
            "info": "#2FA572",     
            "warning": "#F39C12",  
            "error": "#E74C3C"     
        }
        text_color = colors.get(msg_type, "white")
        
        icons = {
            "info": "ℹ️ ",
            "warning": "⚠️ ",
            "error": "❌ "
        }
        icon = icons.get(msg_type, "")
        
        self.lbl_msg = ctk.CTkLabel(
            self, 
            text=f"{icon}{message}", 
            wraplength=400, 
            font=("Arial", 15), 
            text_color=text_color
        )
        self.lbl_msg.pack(pady=40, padx=20, expand=True)
        
        self.btn_ok = ctk.CTkButton(
            self, 
            text="Tamam", 
            command=self.destroy, 
            width=120,
            fg_color=text_color,
            hover_color="#555555"
        )
        self.btn_ok.pack(pady=20)


# --- ARAYÜZ (GUI) TASARIMI ---

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LocalFolderEncryptorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Klasör İçi Dosya Şifreleyici")
        self.geometry("600x620")
        self.resizable(False, False)

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

        self.scroll_frame = ctk.CTkScrollableFrame(self, height=180, label_text="Klasördeki Dosyalar")
        self.scroll_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # --- ŞİFRE GİRİŞ ALANLARI ---
        self.frame_pwd = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_pwd.pack(pady=5)

        self.entry_pwd = ctk.CTkEntry(self.frame_pwd, placeholder_text="Şifre Giriniz", show="*", width=350)
        self.entry_pwd.pack(pady=5)

        # 2. Şifre alanı oluşturulur ancak 'pack' edilmez (gizli başlar)
        self.entry_pwd_confirm = ctk.CTkEntry(self.frame_pwd, placeholder_text="Şifreyi Tekrar Giriniz", show="*", width=350)

        # --- İŞLEM BUTONLARI ---
        self.frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actions.pack(pady=15)

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
        self.entry_pwd_confirm.pack_forget() # Listeyi yenilerken 2. şifreyi gizle

        try:
            all_items = os.listdir(self.current_dir)
            files = []
            ignored_extensions = ('.exe', '.py', '.spec', '.bat', '.cmd')

            for item in all_items:
                full_path = os.path.join(self.current_dir, item)
                if item == "Arşiv" and os.path.isdir(full_path):
                    continue

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
            CustomMessageBox(self, "Hata", f"Klasör taranırken hata oluştu:\n{e}", "error")

    def on_file_select(self):
        self.selected_file = self.radio_var.get()
        
        # Seçilen dosyanın uzantısına göre 2. şifre alanını göster veya gizle
        if self.selected_file.endswith('.enc'):
            self.entry_pwd_confirm.pack_forget()  # Şifreli dosya, 2. alanı gizle
            self.entry_pwd_confirm.delete(0, 'end') # İçini temizle
        else:
            self.entry_pwd_confirm.pack(pady=5)   # Şifresiz dosya, 2. alanı göster

    def encrypt_action(self):
        filename = self.selected_file
        password = self.entry_pwd.get()
        password_confirm = self.entry_pwd_confirm.get()

        if not filename or not password or not password_confirm:
            CustomMessageBox(self, "Eksik Bilgi", "Lütfen bir dosya seçin ve her iki şifre alanını da doldurun.", "warning")
            return

        if password != password_confirm:
            CustomMessageBox(self, "Hata", "Girdiğiniz şifreler birbiriyle uyuşmuyor!", "error")
            return

        if filename.endswith('.enc'):
            CustomMessageBox(self, "Uyarı", "Bu dosya zaten şifrelenmiş görünüyor (.enc uzantılı).", "warning")
            return

        file_path = os.path.join(self.current_dir, filename)

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            encrypted_data = encrypt_bytes(data, password)
            desired_filename = filename + ".enc"
            target_file_path = handle_conflict_and_get_path(self.current_dir, desired_filename)

            with open(target_file_path, "wb") as f:
                f.write(encrypted_data)

            CustomMessageBox(self, "Başarılı", f"Dosya şifrelendi ve ana klasöre kaydedildi:\n{desired_filename}", "info")
            self.entry_pwd.delete(0, 'end')
            self.entry_pwd_confirm.delete(0, 'end')
            self.refresh_file_list()

        except Exception as e:
            CustomMessageBox(self, "Hata", f"Şifreleme sırasında hata oluştu:\n{e}", "error")

    def decrypt_action(self):
        filename = self.selected_file
        password = self.entry_pwd.get()

        if not filename or not password:
            CustomMessageBox(self, "Eksik Bilgi", "Lütfen şifreli bir dosya seçin ve şifre girin.", "warning")
            return

        file_path = os.path.join(self.current_dir, filename)

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            decrypted_data = decrypt_bytes(data, password)

            if filename.endswith('.enc'):
                desired_filename = filename[:-4]
            else:
                desired_filename = "cozulmus_" + filename

            target_file_path = handle_conflict_and_get_path(self.current_dir, desired_filename)

            with open(target_file_path, "wb") as f:
                f.write(decrypted_data)

            CustomMessageBox(self, "Başarılı", f"Dosya şifresi çözüldü ve ana klasöre kaydedildi:\n{desired_filename}", "info")
            self.entry_pwd.delete(0, 'end')
            self.entry_pwd_confirm.delete(0, 'end')
            self.refresh_file_list()

        except Exception:
            CustomMessageBox(self, "Hata", "Şifre yanlış veya dosya bozuk!", "error")

if __name__ == "__main__":
    app = LocalFolderEncryptorApp()
    app.mainloop()