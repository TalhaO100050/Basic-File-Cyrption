import base64
import os
import sys
import tempfile
import subprocess
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

def encrypt_text(plain_text: str, password: str) -> str:
    data = plain_text.encode('utf-8')
    encrypted = encrypt_bytes(data, password)
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_text(encrypted_b64: str, password: str) -> str:
    encrypted_bytes = base64.b64decode(encrypted_b64.encode('utf-8'))
    decrypted_bytes = decrypt_bytes(encrypted_bytes, password)
    return decrypted_bytes.decode('utf-8')

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
        self.title("Klasör ve Metin Şifreleyici")
        self.geometry("660x720")
        self.resizable(False, False)

        if getattr(sys, 'frozen', False):
            self.current_dir = os.path.dirname(sys.executable)
        else:
            self.current_dir = os.path.dirname(os.path.abspath(__file__))

        # Düzenleme sekmesi için durum değişkenleri
        self.current_edit_mode = None  # 'text' veya 'external' olacak
        self.current_temp_file = None

        self.tabview = ctk.CTkTabview(self, width=620, height=680)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        # Sekme sırası değiştirildi
        self.tab_files = self.tabview.add("📄 Dosya Şifreleme")
        self.tab_edit = self.tabview.add("✏️ Şifreli Düzenleme")
        self.tab_text = self.tabview.add("✍️ Metin Şifreleme")

        self.setup_file_tab()
        self.setup_edit_tab()
        self.setup_text_tab()

    # --- SEKME 1: DOSYA ŞİFRELEME ---
    def setup_file_tab(self):
        self.selected_file = None
        self.radio_var = ctk.StringVar(value="")

        self.frame_top = ctk.CTkFrame(self.tab_files, fg_color="transparent")
        self.frame_top.pack(fill="x", padx=10, pady=5)

        self.lbl_path = ctk.CTkLabel(self.frame_top, text=f"📁 Çalışma Alanı: {os.path.basename(self.current_dir)}", font=("Arial", 14, "bold"))
        self.lbl_path.pack(side="left")

        self.btn_refresh = ctk.CTkButton(self.frame_top, text="🔄 Listeyi Yenile", width=110, command=self.refresh_file_list)
        self.btn_refresh.pack(side="right")

        self.lbl_info = ctk.CTkLabel(self.tab_files, text="Şifrelenecek veya çözülecek dosyayı seçin:", text_color="gray")
        self.lbl_info.pack(anchor="w", padx=15, pady=(5, 0))

        self.scroll_frame = ctk.CTkScrollableFrame(self.tab_files, height=200, label_text="Klasördeki Dosyalar")
        self.scroll_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.frame_pwd = ctk.CTkFrame(self.tab_files, fg_color="transparent")
        self.frame_pwd.pack(pady=5)

        self.entry_pwd = ctk.CTkEntry(self.frame_pwd, placeholder_text="Şifre Giriniz", show="*", width=350)
        self.entry_pwd.pack(pady=5)

        self.entry_pwd_confirm = ctk.CTkEntry(self.frame_pwd, placeholder_text="Şifreyi Tekrar Giriniz", show="*", width=350)

        self.frame_actions = ctk.CTkFrame(self.tab_files, fg_color="transparent")
        self.frame_actions.pack(pady=15)

        self.btn_encrypt = ctk.CTkButton(self.frame_actions, text="🔒 Seçileni Şifrele", fg_color="#2FA572", hover_color="#1E6B49", width=160, command=self.encrypt_action)
        self.btn_encrypt.grid(row=0, column=0, padx=10)

        self.btn_decrypt = ctk.CTkButton(self.frame_actions, text="🔓 Şifreyi Çöz", fg_color="#E74C3C", hover_color="#962D22", width=160, command=self.decrypt_action)
        self.btn_decrypt.grid(row=0, column=1, padx=10)

        self.refresh_file_list()

    def refresh_file_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.radio_var.set("")
        self.selected_file = None
        self.entry_pwd_confirm.pack_forget()

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
            else:
                for file_name in files:
                    display_text = f"🔒 {file_name}" if file_name.endswith('.enc') else f"📄 {file_name}"
                    rb = ctk.CTkRadioButton(self.scroll_frame, text=display_text, value=file_name, variable=self.radio_var, command=self.on_file_select)
                    rb.pack(anchor="w", pady=5, padx=10)

            if hasattr(self, 'option_enc_files'):
                self.refresh_edit_file_list()

        except Exception as e:
            CustomMessageBox(self, "Hata", f"Klasör taranırken hata oluştu:\n{e}", "error")

    def on_file_select(self):
        self.selected_file = self.radio_var.get()
        if self.selected_file.endswith('.enc'):
            self.entry_pwd_confirm.pack_forget()
            self.entry_pwd_confirm.delete(0, 'end')
        else:
            self.entry_pwd_confirm.pack(pady=5)

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
            desired_filename = filename[:-4] if filename.endswith('.enc') else "cozulmus_" + filename
            target_file_path = handle_conflict_and_get_path(self.current_dir, desired_filename)

            with open(target_file_path, "wb") as f:
                f.write(decrypted_data)

            CustomMessageBox(self, "Başarılı", f"Dosya şifresi çözüldü:\n{desired_filename}", "info")
            self.entry_pwd.delete(0, 'end')
            self.entry_pwd_confirm.delete(0, 'end')
            self.refresh_file_list()
        except Exception:
            CustomMessageBox(self, "Hata", "Şifre yanlış veya dosya bozuk!", "error")

    # --- SEKME 2 (YENİ SIRA): ŞİFRELİ DOSYA DÜZENLEME ---
    def setup_edit_tab(self):
        self.frame_edit_file = ctk.CTkFrame(self.tab_edit, fg_color="transparent")
        self.frame_edit_file.pack(fill="x", padx=10, pady=(10, 5))

        self.lbl_edit_select = ctk.CTkLabel(self.frame_edit_file, text="Şifreli Dosya (.enc):", text_color="gray")
        self.lbl_edit_select.pack(side="left", padx=(0, 5))

        self.option_enc_files = ctk.CTkOptionMenu(
            self.frame_edit_file, 
            values=["Seçiniz"], 
            width=280,
            command=self.on_edit_file_changed
        )
        self.option_enc_files.pack(side="left", padx=5)

        self.btn_edit_refresh = ctk.CTkButton(self.frame_edit_file, text="🔄 Yenile", width=80, command=self.refresh_edit_file_list)
        self.btn_edit_refresh.pack(side="left", padx=5)

        self.frame_edit_pwd = ctk.CTkFrame(self.tab_edit, fg_color="transparent")
        self.frame_edit_pwd.pack(fill="x", padx=10, pady=5)

        self.entry_edit_pwd = ctk.CTkEntry(self.frame_edit_pwd, placeholder_text="Şifre Giriniz", show="*", width=310)
        self.entry_edit_pwd.pack(side="left", padx=(0, 10))

        self.btn_edit_load = ctk.CTkButton(self.frame_edit_pwd, text="🔓 Aç ve Düzenle", fg_color="#3498DB", hover_color="#2980B9", width=150, command=self.load_and_decrypt_edit_file)
        self.btn_edit_load.pack(side="left")

        self.lbl_edit_status = ctk.CTkLabel(self.tab_edit, text="", font=("Arial", 13, "bold"))
        self.lbl_edit_status.pack(pady=5)

        self.txt_edit = ctk.CTkTextbox(self.tab_edit, height=240)
        self.txt_edit.pack(fill="both", expand=True, padx=10, pady=5)

        self.frame_edit_bottom = ctk.CTkFrame(self.tab_edit, fg_color="transparent")
        self.frame_edit_bottom.pack(pady=10)

        self.btn_edit_save = ctk.CTkButton(self.frame_edit_bottom, text="💾 Kaydet ve Şifrele", fg_color="#2FA572", hover_color="#1E6B49", width=200, height=35, font=("Arial", 14, "bold"), command=self.save_and_encrypt_edit_file)
        self.btn_edit_save.pack()

        self.refresh_edit_file_list()

    def on_edit_file_changed(self, choice):
        self.current_edit_mode = None
        self.current_temp_file = None
        self.txt_edit.configure(state="normal")
        self.txt_edit.delete("1.0", "end")
        self.lbl_edit_status.configure(text="", text_color="white")

    def refresh_edit_file_list(self):
        try:
            all_items = os.listdir(self.current_dir)
            enc_files = [item for item in all_items if item.endswith('.enc') and os.path.isfile(os.path.join(self.current_dir, item))]
            
            if enc_files:
                self.option_enc_files.configure(values=enc_files)
                if self.option_enc_files.get() not in enc_files:
                    self.option_enc_files.set(enc_files[0])
            else:
                self.option_enc_files.configure(values=[".enc dosyası bulunamadı"])
                self.option_enc_files.set(".enc dosyası bulunamadı")
        except Exception as e:
            pass

    def load_and_decrypt_edit_file(self):
        filename = self.option_enc_files.get()
        password = self.entry_edit_pwd.get()

        if not filename or filename == ".enc dosyası bulunamadı" or filename == "Seçiniz":
            self.lbl_edit_status.configure(text="Lütfen geçerli bir .enc dosyası seçin.", text_color="#E74C3C")
            return

        if not password:
            self.lbl_edit_status.configure(text="Lütfen şifrenizi girin.", text_color="#E74C3C")
            return

        file_path = os.path.join(self.current_dir, filename)

        try:
            with open(file_path, "rb") as f:
                data = f.read()
            decrypted_bytes = decrypt_bytes(data, password)
        except Exception:
            self.lbl_edit_status.configure(text="Geçersiz Şifre veya okunamayan dosya!", text_color="#E74C3C")
            return

        self.txt_edit.configure(state="normal")
        self.txt_edit.delete("1.0", "end")
        
        try:
            decrypted_text = decrypted_bytes.decode('utf-8')
            
            # --- METİN MODU ---
            self.current_edit_mode = "text"
            self.txt_edit.insert("1.0", decrypted_text)
            self.lbl_edit_status.configure(text=f"'{filename}' (Metin) açıldı. Düzenleyip kaydedebilirsiniz.", text_color="#2FA572")
            
        except UnicodeDecodeError:
            # --- DIŞ UYGULAMA (BİNARY) MODU ---
            self.current_edit_mode = "external"
            base_name = filename[:-4]  # ".enc" kısmını at
            
            temp_dir = tempfile.gettempdir()
            self.current_temp_file = os.path.join(temp_dir, f"enc_temp_{base_name}")
            
            with open(self.current_temp_file, "wb") as f:
                f.write(decrypted_bytes)
                
            if sys.platform == "win32":
                os.startfile(self.current_temp_file)
            elif sys.platform == "darwin":
                subprocess.call(["open", self.current_temp_file])
            else:
                subprocess.call(["xdg-open", self.current_temp_file])
                
            info_message = (
                f"⚠️ Bu dosya metin tabanlı değil!\n\n"
                f"'{base_name}' sisteminizin varsayılan uygulamasıyla açıldı.\n"
                f"(Örn: Word, Excel, Fotoğraf görüntüleyici vb.)\n\n"
                f"1. Açılan programda dosyanızı düzenleyin.\n"
                f"2. Değişiklikleri kaydedin (Ctrl+S / Dosya > Kaydet).\n"
                f"3. İlgili programı kapatın.\n"
                f"4. Aşağıdaki '💾 Kaydet ve Şifrele' butonuna basarak işleminizi tamamlayın."
            )
            self.txt_edit.insert("1.0", info_message)
            self.txt_edit.configure(state="disabled")
            
            self.lbl_edit_status.configure(text=f"'{filename}' dış uygulamada açıldı.", text_color="#F39C12")


    def save_and_encrypt_edit_file(self):
        filename = self.option_enc_files.get()
        password = self.entry_edit_pwd.get()

        if not self.current_edit_mode:
            self.lbl_edit_status.configure(text="Lütfen önce bir dosyayı 'Aç ve Düzenle' butonu ile açın.", text_color="#E74C3C")
            return

        if not password:
            self.lbl_edit_status.configure(text="Kaydetmek için şifrenizi girin.", text_color="#E74C3C")
            return

        file_path = os.path.join(self.current_dir, filename)

        try:
            if self.current_edit_mode == "text":
                text_content = self.txt_edit.get("1.0", "end-1c")
                raw_bytes = text_content.encode('utf-8')
                
            elif self.current_edit_mode == "external":
                if not os.path.exists(self.current_temp_file):
                    self.lbl_edit_status.configure(text="Geçici dosya bulunamadı! Lütfen tekrar açın.", text_color="#E74C3C")
                    return
                with open(self.current_temp_file, "rb") as f:
                    raw_bytes = f.read()

            encrypted_data = encrypt_bytes(raw_bytes, password)

            with open(file_path, "wb") as f:
                f.write(encrypted_data)

            if self.current_edit_mode == "external":
                try:
                    os.remove(self.current_temp_file)
                except Exception:
                    pass 
                self.txt_edit.configure(state="normal")
                self.txt_edit.delete("1.0", "end")

            self.current_edit_mode = None
            self.current_temp_file = None
            self.lbl_edit_status.configure(text=f"'{filename}' başarıyla kaydedildi ve şifrelendi!", text_color="#2FA572")

        except Exception as e:
            self.lbl_edit_status.configure(text=f"Kaydetme hatası: {e}", text_color="#E74C3C")


    # --- SEKME 3 (YENİ SIRA): METİN ŞİFRELEME ---
    def setup_text_tab(self):
        self.lbl_text_input = ctk.CTkLabel(self.tab_text, text="Giriş Metni / Şifreli Metin:", text_color="gray")
        self.lbl_text_input.pack(anchor="w", padx=10, pady=(10, 2))

        self.txt_input = ctk.CTkTextbox(self.tab_text, height=120)
        self.txt_input.pack(fill="x", padx=10, pady=2)

        self.frame_text_pwd = ctk.CTkFrame(self.tab_text, fg_color="transparent")
        self.frame_text_pwd.pack(pady=10)

        self.entry_text_pwd = ctk.CTkEntry(self.frame_text_pwd, placeholder_text="Şifre Giriniz", width=350)
        self.entry_text_pwd.pack(pady=5)

        self.frame_text_actions = ctk.CTkFrame(self.tab_text, fg_color="transparent")
        self.frame_text_actions.pack(pady=5)

        self.btn_text_encrypt = ctk.CTkButton(self.frame_text_actions, text="🔒 Metni Şifrele", fg_color="#2FA572", hover_color="#1E6B49", width=150, command=self.encrypt_text_action)
        self.btn_text_encrypt.grid(row=0, column=0, padx=10)

        self.btn_text_decrypt = ctk.CTkButton(self.frame_text_actions, text="🔓 Şifreyi Çöz", fg_color="#E74C3C", hover_color="#962D22", width=150, command=self.decrypt_text_action)
        self.btn_text_decrypt.grid(row=0, column=1, padx=10)

        self.lbl_text_output = ctk.CTkLabel(self.tab_text, text="Sonuç:", text_color="gray")
        self.lbl_text_output.pack(anchor="w", padx=10, pady=(10, 2))

        self.txt_output = ctk.CTkTextbox(self.tab_text, height=120)
        self.txt_output.pack(fill="x", padx=10, pady=2)

        self.frame_text_utility = ctk.CTkFrame(self.tab_text, fg_color="transparent")
        self.frame_text_utility.pack(pady=10)

        self.btn_copy = ctk.CTkButton(self.frame_text_utility, text="📋 Sonucu Kopyala", width=140, fg_color="#3498DB", hover_color="#2980B9", command=self.copy_result)
        self.btn_copy.grid(row=0, column=0, padx=10)

        self.btn_clear = ctk.CTkButton(self.frame_text_utility, text="🧹 Temizle", width=100, fg_color="#7F8C8D", hover_color="#626567", command=self.clear_text_fields)
        self.btn_clear.grid(row=0, column=1, padx=10)

    def encrypt_text_action(self):
        raw_text = self.txt_input.get("1.0", "end-1c").strip()
        pwd = self.entry_text_pwd.get()
        if not raw_text or not pwd:
            return
        try:
            encrypted_str = encrypt_text(raw_text, pwd)
            self.txt_output.configure(text_color="#DCE4EE")
            self.txt_output.delete("1.0", "end")
            self.txt_output.insert("1.0", encrypted_str)
        except Exception as e:
            pass

    def decrypt_text_action(self):
        encrypted_str = self.txt_input.get("1.0", "end-1c").strip()
        pwd = self.entry_text_pwd.get()
        if not encrypted_str or not pwd:
            return
        try:
            decrypted_str = decrypt_text(encrypted_str, pwd)
            self.txt_output.configure(text_color="#DCE4EE")
            self.txt_output.delete("1.0", "end")
            self.txt_output.insert("1.0", decrypted_str)
        except Exception:
            self.txt_output.configure(text_color="#E74C3C")
            self.txt_output.delete("1.0", "end")
            self.txt_output.insert("1.0", "Geçersiz Şifre!")

    def copy_result(self):
        output_str = self.txt_output.get("1.0", "end-1c").strip()
        if output_str:
            self.clipboard_clear()
            self.clipboard_append(output_str)

    def clear_text_fields(self):
        self.txt_input.delete("1.0", "end")
        self.txt_output.configure(text_color="#DCE4EE")
        self.txt_output.delete("1.0", "end")
        self.entry_text_pwd.delete(0, "end")


if __name__ == "__main__":
    app = LocalFolderEncryptorApp()
    app.mainloop()