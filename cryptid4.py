import base64
import os
import sys
import subprocess
import tempfile
import shutil
from tkinter import filedialog
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend

import customtkinter as ctk

# --- ŞİFRELEME FONKSİYONLARI ---

MAGIC_STRING = b"VAULT_OK"

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


# --- MESAJ KUTUSU (DİNAMİK BOYUT VE MERKEZLEME) ---
class CustomMessageBox(ctk.CTkToplevel):
    def __init__(self, master, title="Mesaj", message="", msg_type="info"):
        super().__init__(master)
        self.withdraw()  # Pencere ekranda belirmeden önce gizle
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        colors = {"info": "#2FA572", "warning": "#F39C12", "error": "#E74C3C"}
        icons = {"info": "ℹ️ ", "warning": "⚠️ ", "error": "❌ "}
        
        text_color = colors.get(msg_type, "white")
        icon = icons.get(msg_type, "")
        
        self.lbl_msg = ctk.CTkLabel(
            self, text=f"{icon}{message}", wraplength=400, 
            font=("Arial", 14), text_color=text_color
        )
        self.lbl_msg.pack(pady=40, padx=30, expand=True)
        
        self.btn_ok = ctk.CTkButton(
            self, text="Tamam", command=self.destroy, width=120,
            fg_color=text_color, hover_color="#555555"
        )
        self.btn_ok.pack(pady=(0, 25))

        self.update_idletasks()
        master.update_idletasks()

        b_w = self.winfo_reqwidth()
        b_h = self.winfo_reqheight()
        a_w = master.winfo_width()
        a_h = master.winfo_height()
        master_x = master.winfo_x()
        master_y = master.winfo_y()

        x = master_x + (a_w / 2 - b_w / 2)
        y = master_y + (a_h / 2 - b_h / 2)

        self.geometry(f"{b_w}x{b_h}+{int(x)}+{int(y)}")
        self.deiconify()


# --- ONAY KUTUSU (EVET/İPTAL) ---
class CustomConfirmBox(ctk.CTkToplevel):
    def __init__(self, master, title="Onay", message="", msg_type="warning"):
        super().__init__(master)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        self.result = False
        
        colors = {"info": "#2FA572", "warning": "#F39C12", "error": "#E74C3C"}
        icons = {"info": "ℹ️ ", "warning": "⚠️ ", "error": "❌ "}
        
        text_color = colors.get(msg_type, "white")
        icon = icons.get(msg_type, "")
        
        self.lbl_msg = ctk.CTkLabel(
            self, text=f"{icon}{message}", wraplength=400, 
            font=("Arial", 14), text_color=text_color
        )
        self.lbl_msg.pack(pady=40, padx=30, expand=True)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 25), padx=30, fill="x")
        
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        
        self.btn_yes = ctk.CTkButton(
            btn_frame, text="Evet", command=self.on_yes, width=120,
            fg_color="#E74C3C", hover_color="#962D22"
        )
        self.btn_yes.grid(row=0, column=0, padx=5)
        
        self.btn_no = ctk.CTkButton(
            btn_frame, text="İptal", command=self.on_no, width=120,
            fg_color="#555555", hover_color="#333333"
        )
        self.btn_no.grid(row=0, column=1, padx=5)

        self.update_idletasks()
        master.update_idletasks()
        b_w = self.winfo_reqwidth()
        b_h = self.winfo_reqheight()
        a_w = master.winfo_width()
        a_h = master.winfo_height()
        master_x = master.winfo_x()
        master_y = master.winfo_y()
        x = master_x + (a_w / 2 - b_w / 2)
        y = master_y + (a_h / 2 - b_h / 2)
        self.geometry(f"{b_w}x{b_h}+{int(x)}+{int(y)}")
        self.deiconify()
        
        self.master.wait_window(self)

    def on_yes(self):
        self.result = True
        self.destroy()

    def on_no(self):
        self.result = False
        self.destroy()


# --- ANA UYGULAMA ---

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SecureVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Korumalı Kasa (Vault) Yöneticisi")
        self.geometry("600x720")
        self.resizable(False, False)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        if getattr(sys, 'frozen', False):
            self.current_dir = os.path.dirname(sys.executable)
        else:
            self.current_dir = os.path.dirname(os.path.abspath(__file__))

        self.vault_password = None
        self.current_vault_path = None
        
        self.active_temp_file = None
        self.active_vault_file = None
        self.radio_var = ctk.StringVar(value="")

        self.setup_login_frame()
        self.setup_vault_frame()

        self.show_login_frame()

    # ================= LOGIN FRAME (GİRİŞ EKRANI) =================
    def setup_login_frame(self):
        self.frame_login = ctk.CTkFrame(self, fg_color="transparent")
        
        self.lbl_title = ctk.CTkLabel(self.frame_login, text="🔒 Kasa Girişi", font=("Arial", 22, "bold"))
        self.lbl_title.pack(pady=(30, 10))
        
        self.lbl_desc = ctk.CTkLabel(self.frame_login, text="Bulunduğunuz dizindeki bir klasörü seçin.\nEğer klasör korumalı değilse yeni şifreyle korumaya alınacaktır.", text_color="gray")
        self.lbl_desc.pack(pady=(0, 20))

        self.option_folders = ctk.CTkOptionMenu(self.frame_login, width=300, command=self.on_folder_changed)
        self.option_folders.pack(pady=10)
        
        self.lbl_status = ctk.CTkLabel(self.frame_login, text="Durum: Bilinmiyor", font=("Arial", 12))
        self.lbl_status.pack(pady=5)

        self.entry_pwd = ctk.CTkEntry(self.frame_login, placeholder_text="Şifre", show="*", width=300, height=40, font=("Arial", 14))
        self.entry_pwd.pack(pady=10)

        # 2. Şifre Doğrulama Kutusu
        self.entry_pwd_confirm = ctk.CTkEntry(self.frame_login, placeholder_text="Şifreyi Tekrar Girin", show="*", width=300, height=40, font=("Arial", 14))

        self.btn_login = ctk.CTkButton(self.frame_login, text="Giriş Yap", width=300, height=45, font=("Arial", 15, "bold"), command=self.login_or_create_vault)
        self.btn_login.pack(pady=15)
        
        self.btn_refresh = ctk.CTkButton(self.frame_login, text="🔄 Klasörleri Yenile", fg_color="transparent", border_width=1, command=self.refresh_folders)
        self.btn_refresh.pack(pady=5)

    def refresh_folders(self):
        try:
            items = os.listdir(self.current_dir)
            folders = [f for f in items if os.path.isdir(os.path.join(self.current_dir, f)) and not f.startswith('.')]

            if folders:
                self.option_folders.configure(values=folders)
                self.option_folders.set(folders[0])
                self.on_folder_changed(folders[0])
            else:
                self.option_folders.configure(values=["Klasör bulunamadı"])
                self.option_folders.set("Klasör bulunamadı")
                self.lbl_status.configure(text="Klasör yok", text_color="gray")
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Hata:\n{e}", "error")

    def on_folder_changed(self, folder_name):
        if folder_name == "Klasör bulunamadı":
            return
            
        folder_path = os.path.join(self.current_dir, folder_name)
        vault_check_path = os.path.join(folder_path, ".vault_check")
        
        if os.path.exists(vault_check_path):
            self.lbl_status.configure(text="Durum: 🔴 Korumalı Kasa (Giriş Yapın)", text_color="#E74C3C")
            self.btn_login.configure(text="🔓 Kasaya Giriş Yap", fg_color="#3498DB", hover_color="#2980B9")
            self.entry_pwd.configure(placeholder_text="Kasa Şifresini Girin")
            self.entry_pwd_confirm.pack_forget()
        else:
            self.lbl_status.configure(text="Durum: 🟢 Korumasız Klasör (Yeni Kasa Oluştur)", text_color="#2FA572")
            self.btn_login.configure(text="🔒 Kasa Oluştur ve Şifrele", fg_color="#2FA572", hover_color="#1E6B49")
            self.entry_pwd.configure(placeholder_text="Yeni Kasa Şifresi Belirleyin")
            self.entry_pwd_confirm.pack(after=self.entry_pwd, pady=10)

    def login_or_create_vault(self):
        folder_name = self.option_folders.get()
        pwd = self.entry_pwd.get()
        
        if folder_name == "Klasör bulunamadı": return
        if not pwd:
            CustomMessageBox(self, "Uyarı", "Lütfen şifre girin!", "warning")
            return
            
        folder_path = os.path.join(self.current_dir, folder_name)
        vault_check_path = os.path.join(folder_path, ".vault_check")

        if os.path.exists(vault_check_path):
            try:
                with open(vault_check_path, "rb") as f:
                    enc_magic = f.read()
                decrypted_magic = decrypt_bytes(enc_magic, pwd)
                if decrypted_magic != MAGIC_STRING:
                    raise ValueError()
                
                self.vault_password = pwd
                self.current_vault_path = folder_path
                self.entry_pwd.delete(0, 'end')
                self.entry_pwd_confirm.delete(0, 'end')
                self.show_vault_frame()
                
            except Exception:
                CustomMessageBox(self, "Hata", "Yanlış Şifre!", "error")
        else:
            pwd_confirm = self.entry_pwd_confirm.get()
            if pwd != pwd_confirm:
                CustomMessageBox(self, "Hata", "Girdiğiniz şifreler birbiriyle eşleşmiyor!", "error")
                return

            try:
                enc_magic = encrypt_bytes(MAGIC_STRING, pwd)
                with open(vault_check_path, "wb") as f:
                    f.write(enc_magic)
                    
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file == ".vault_check" or file.endswith(".enc"): continue
                        file_path = os.path.join(root, file)
                        with open(file_path, "rb") as f: data = f.read()
                        enc_data = encrypt_bytes(data, pwd)
                        with open(file_path + ".enc", "wb") as f: f.write(enc_data)
                        os.remove(file_path)

                self.vault_password = pwd
                self.current_vault_path = folder_path
                self.entry_pwd.delete(0, 'end')
                self.entry_pwd_confirm.delete(0, 'end')
                CustomMessageBox(self, "Başarılı", "Kasa oluşturuldu ve dosyalar şifrelendi!", "info")
                self.show_vault_frame()
            except Exception as e:
                CustomMessageBox(self, "Hata", f"Kasa oluşturulamadı:\n{e}", "error")

    # ================= VAULT FRAME (İÇ EKRAN) =================
    def setup_vault_frame(self):
        self.frame_vault = ctk.CTkFrame(self, fg_color="transparent")
        
        self.frame_vault_top = ctk.CTkFrame(self.frame_vault, fg_color="transparent")
        self.frame_vault_top.pack(fill="x", padx=20, pady=10)
        
        self.lbl_vault_name = ctk.CTkLabel(self.frame_vault_top, text="Açık Kasa: ", font=("Arial", 16, "bold"))
        self.lbl_vault_name.pack(side="left")
        
        self.btn_logout = ctk.CTkButton(self.frame_vault_top, text="Çıkış Yap / Kilitle", width=120, fg_color="#E74C3C", hover_color="#962D22", command=self.logout)
        self.btn_logout.pack(side="right")

        self.scroll_files = ctk.CTkScrollableFrame(self.frame_vault, height=220, label_text="Kasadaki Dosyalar")
        self.scroll_files.pack(fill="x", padx=20, pady=5)

        self.frame_vault_controls = ctk.CTkFrame(self.frame_vault, fg_color="transparent")
        self.frame_vault_controls.pack(fill="x", padx=20, pady=5)
        
        self.frame_vault_controls.grid_columnconfigure(0, weight=1)
        self.frame_vault_controls.grid_columnconfigure(1, weight=1)

        self.btn_add_file = ctk.CTkButton(self.frame_vault_controls, text="➕ Kasaya Dosya Ekle", fg_color="#2FA572", hover_color="#1E6B49", command=self.add_file_to_vault)
        self.btn_add_file.grid(row=0, column=0, padx=5, pady=5, sticky="we")
        
        self.btn_open_file = ctk.CTkButton(self.frame_vault_controls, text="🔓 Seçileni Aç / Düzenle", fg_color="#3498DB", hover_color="#2980B9", command=self.open_file_from_vault)
        self.btn_open_file.grid(row=0, column=1, padx=5, pady=5, sticky="we")
        
        self.btn_export_file = ctk.CTkButton(self.frame_vault_controls, text="📤 Şifresiz Dışa Aktar", fg_color="#9B59B6", hover_color="#8E44AD", command=self.export_file_from_vault)
        self.btn_export_file.grid(row=1, column=0, padx=5, pady=5, sticky="we")

        self.btn_del_file = ctk.CTkButton(self.frame_vault_controls, text="🗑️ Seçileni Sil", fg_color="transparent", border_width=1, text_color="#E74C3C", border_color="#E74C3C", hover_color="#3A1C1C", command=self.delete_file_from_vault)
        self.btn_del_file.grid(row=1, column=1, padx=5, pady=5, sticky="we")

        # Aktif Dosya Paneli
        self.frame_active = ctk.CTkFrame(self.frame_vault, fg_color="#2B2B2B", border_width=1, border_color="#F39C12")
        
        self.lbl_active_info = ctk.CTkLabel(self.frame_active, text="⚠️ Şu an bir dosya açık. Düzenleme yapabilirsiniz.", text_color="#F39C12", font=("Arial", 12, "bold"))
        self.lbl_active_info.pack(pady=(8, 2))
        
        self.lbl_active_filename = ctk.CTkLabel(self.frame_active, text="Dosya: none.txt")
        self.lbl_active_filename.pack(pady=2)
        
        self.btn_save_close = ctk.CTkButton(self.frame_active, text="💾 Değişiklikleri Kaydet ve Kapat", fg_color="#2FA572", hover_color="#1E6B49", width=250, command=self.save_and_close_active_file)
        self.btn_save_close.pack(pady=(5, 5))

        self.btn_close_without_saving = ctk.CTkButton(self.frame_active, text="❌ Değişiklikleri Kaydetmeden Kapat", fg_color="#E74C3C", hover_color="#962D22", width=250, command=self.close_without_saving_active_file)
        self.btn_close_without_saving.pack(pady=(0, 10))


    def refresh_vault_files(self):
        for widget in self.scroll_files.winfo_children():
            widget.destroy()
        
        self.radio_var.set("")
        
        try:
            files = [f for f in os.listdir(self.current_vault_path) if f.endswith('.enc')]
            if not files:
                lbl = ctk.CTkLabel(self.scroll_files, text="Kasa boş.", text_color="gray")
                lbl.pack(pady=20)
                return
                
            for file in files:
                display_name = file[:-4]
                rb = ctk.CTkRadioButton(self.scroll_files, text=f"📄 {display_name}", value=file, variable=self.radio_var)
                rb.pack(anchor="w", pady=5, padx=10)
        except Exception as e:
            pass

    def add_file_to_vault(self):
        file_paths = filedialog.askopenfilenames(title="Kasaya Eklenecek Dosyaları Seçin")
        if not file_paths: return
        
        try:
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    data = f.read()
                
                enc_data = encrypt_bytes(data, self.vault_password)
                target_path = os.path.join(self.current_vault_path, file_name + ".enc")
                
                with open(target_path, "wb") as f:
                    f.write(enc_data)
                    
            CustomMessageBox(self, "Başarılı", "Dosyalar şifrelenerek kasaya kopyalandı.", "info")
            self.refresh_vault_files()
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Dosya eklenirken hata:\n{e}", "error")

    def open_file_from_vault(self):
        if self.active_temp_file:
            CustomMessageBox(self, "Uyarı", "Önce açık olan dosyayı kapatmalısınız!", "warning")
            return
            
        selected_file = self.radio_var.get()
        if not selected_file:
            CustomMessageBox(self, "Uyarı", "Lütfen açmak için bir dosya seçin.", "warning")
            return

        enc_file_path = os.path.join(self.current_vault_path, selected_file)
        original_name = selected_file[:-4]
        
        try:
            with open(enc_file_path, "rb") as f:
                enc_data = f.read()
            dec_data = decrypt_bytes(enc_data, self.vault_password)
            
            temp_dir = tempfile.gettempdir()
            self.active_temp_file = os.path.join(temp_dir, f"VAULT_{original_name}")
            self.active_vault_file = enc_file_path
            
            with open(self.active_temp_file, "wb") as f:
                f.write(dec_data)
                
            if sys.platform == "win32":
                os.startfile(self.active_temp_file)
            elif sys.platform == "darwin":
                subprocess.call(["open", self.active_temp_file])
            else:
                subprocess.call(["xdg-open", self.active_temp_file])

            self.btn_open_file.configure(state="disabled")
            self.lbl_active_filename.configure(text=f"Açık Dosya: {original_name}")
            self.frame_active.pack(fill="x", padx=20, pady=5)
            
        except Exception as e:
            self.active_temp_file = None
            self.active_vault_file = None
            CustomMessageBox(self, "Hata", f"Dosya açılamadı:\n{e}", "error")

    def export_file_from_vault(self):
        selected_file = self.radio_var.get()
        if not selected_file:
            CustomMessageBox(self, "Uyarı", "Lütfen dışa aktarmak için bir dosya seçin.", "warning")
            return
            
        export_dir = filedialog.askdirectory(title="Dosyanın Kaydedileceği Klasörü Seçin")
        if not export_dir:
            return

        enc_file_path = os.path.join(self.current_vault_path, selected_file)
        original_name = selected_file[:-4]
        target_path = os.path.join(export_dir, original_name)
        
        try:
            with open(enc_file_path, "rb") as f:
                enc_data = f.read()
            dec_data = decrypt_bytes(enc_data, self.vault_password)
            
            with open(target_path, "wb") as f:
                f.write(dec_data)
                
            CustomMessageBox(self, "Başarılı", f"Dosya şifresiz olarak dışa aktarıldı:\n{target_path}", "info")
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Dosya dışa aktarılamadı:\n{e}", "error")

    def save_and_close_active_file(self):
        if not self.active_temp_file or not os.path.exists(self.active_temp_file):
            CustomMessageBox(self, "Hata", "Geçici dosya bulunamadı! Değişiklik yapılamadı.", "error")
            self.reset_active_state()
            return
            
        try:
            with open(self.active_temp_file, "rb") as f:
                new_data = f.read()
                
            enc_data = encrypt_bytes(new_data, self.vault_password)
            with open(self.active_vault_file, "wb") as f:
                f.write(enc_data)
                
            CustomMessageBox(self, "Başarılı", "Dosya güncellendi, şifrelendi ve kapatıldı.", "info")
            
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Dosya kaydedilirken hata oluştu:\n{e}", "error")
            
        self.reset_active_state()
        self.refresh_vault_files()

    def close_without_saving_active_file(self):
        if not self.active_temp_file:
            self.reset_active_state()
            return
            
        original_name = os.path.basename(self.active_vault_file)[:-4] if self.active_vault_file else "Dosya"
        
        # Silme işlemindeki gibi onay penceresi
        confirm = CustomConfirmBox(
            self, 
            "Değişiklikleri Atma Onay", 
            f"'{original_name}' dosyasında yaptığınız değişiklikleri kaydetmeden kapatmak istediğinize emin misiniz? Yapılan değişiklikler kaybolacak.", 
            "warning"
        )
        if not confirm.result:
            return
            
        self.reset_active_state()
        CustomMessageBox(self, "Bilgi", "Dosya kapatıldı, değişiklikler kaydedilmedi.", "info")
        self.refresh_vault_files()

    def reset_active_state(self):
        if self.active_temp_file and os.path.exists(self.active_temp_file):
            try:
                os.remove(self.active_temp_file)
            except:
                pass
                
        self.active_temp_file = None
        self.active_vault_file = None
        self.btn_open_file.configure(state="normal")
        self.frame_active.pack_forget()

    def delete_file_from_vault(self):
        selected_file = self.radio_var.get()
        if not selected_file:
            CustomMessageBox(self, "Uyarı", "Lütfen silinecek bir dosya seçin.", "warning")
            return
            
        if self.active_vault_file and selected_file in self.active_vault_file:
            CustomMessageBox(self, "Uyarı", "Bu dosya şu an açık! Önce kapatın.", "warning")
            return
            
        original_name = selected_file[:-4]
        
        confirm = CustomConfirmBox(
            self, 
            "Silme Onayı", 
            f"'{original_name}' dosyasını kasadan kalıcı olarak silmek istediğinize emin misiniz?", 
            "warning"
        )
        if not confirm.result:
            return
            
        target = os.path.join(self.current_vault_path, selected_file)
        try:
            os.remove(target)
            self.refresh_vault_files()
            CustomMessageBox(self, "Başarılı", f"'{original_name}' kasadan başarıyla silindi.", "info")
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Silinemedi:\n{e}", "error")

    def logout(self):
        if self.active_temp_file:
            CustomMessageBox(self, "Uyarı", "Çıkış yapmadan önce açık olan dosyanızı kapatmalısınız!", "warning")
            return
            
        self.vault_password = None
        self.current_vault_path = None
        self.show_login_frame()

    # ================= EKRAN DEĞİŞİMİ VE KAPANIŞ =================
    def show_login_frame(self):
        self.frame_vault.pack_forget()
        self.refresh_folders()
        self.frame_login.pack(fill="both", expand=True)

    def show_vault_frame(self):
        self.frame_login.pack_forget()
        folder_name = os.path.basename(self.current_vault_path)
        self.lbl_vault_name.configure(text=f"📂 Açık Kasa: {folder_name}")
        self.refresh_vault_files()
        self.frame_vault.pack(fill="both", expand=True)

    def on_closing(self):
        if self.active_temp_file and os.path.exists(self.active_temp_file):
            try:
                os.remove(self.active_temp_file)
            except:
                pass
        self.destroy()

if __name__ == "__main__":
    app = SecureVaultApp()
    app.mainloop()