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


# --- YARDIMCI MERKEZLEME FONKSİYONU (POP-UP'LAR İÇİN) ---
def center_toplevel_over_master(popup, master):
    popup.update_idletasks()
    master.update_idletasks()

    scaling = popup._get_window_scaling()

    b_w = popup.winfo_reqwidth()
    b_h = popup.winfo_reqheight()
    scaled_b_w = int(b_w * scaling)
    scaled_b_h = int(b_h * scaling)

    master_x = master.winfo_rootx()
    master_y = master.winfo_rooty()
    master_w = master.winfo_width()
    master_h = master.winfo_height()

    x = master_x + int((master_w - scaled_b_w) / 2)
    y = master_y + int((master_h - scaled_b_h) / 2)

    popup.geometry(f"{b_w}x{b_h}+{x}+{y}")


# --- MESAJ KUTUSU ---
class CustomMessageBox(ctk.CTkToplevel):
    def __init__(self, master, title="Mesaj", message="", msg_type="info"):
        super().__init__(master)
        self.withdraw()
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

        center_toplevel_over_master(self, master)
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

        center_toplevel_over_master(self, master)
        self.deiconify()
        
        self.master.wait_window(self)

    def on_yes(self):
        self.result = True
        self.destroy()

    def on_no(self):
        self.result = False
        self.destroy()


# --- ÖZEL GİRİŞ KUTUSU ---
class CustomInputDialog(ctk.CTkToplevel):
    def __init__(self, master, title="Giriş", text="", initial_value="", select_to_ext=False, ext_length=0):
        super().__init__(master)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        self.result = None
        
        self.lbl = ctk.CTkLabel(self, text=text, font=("Arial", 14))
        self.lbl.pack(pady=(25, 10), padx=30, anchor="w")
        
        self.entry = ctk.CTkEntry(self, width=350, height=35, font=("Arial", 14))
        self.entry.pack(pady=10, padx=30)
        
        if initial_value:
            self.entry.insert(0, initial_value)
            
        if select_to_ext and ext_length > 0:
            select_end = len(initial_value) - ext_length
            if select_end > 0:
                self.entry.after(100, lambda: self.apply_selection(0, select_end))
            else:
                self.entry.after(100, lambda: self.apply_selection(0, 'end'))
        else:
            self.entry.after(100, lambda: self.apply_selection(0, 'end'))
            
        self.entry.focus()
        self.entry.bind("<Return>", lambda e: self.on_ok())
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(10, 25), padx=30, fill="x")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        
        self.btn_ok = ctk.CTkButton(
            btn_frame, text="Tamam", command=self.on_ok, width=120,
            fg_color="#2FA572", hover_color="#1E6B49"
        )
        self.btn_ok.grid(row=0, column=0, padx=5)
        
        self.btn_cancel = ctk.CTkButton(
            btn_frame, text="İptal", command=self.destroy, width=120,
            fg_color="#555555", hover_color="#333333"
        )
        self.btn_cancel.grid(row=0, column=1, padx=5)

        center_toplevel_over_master(self, master)
        self.deiconify()
        
        self.master.wait_window(self)

    def apply_selection(self, start, end):
        self.entry.focus_set()
        self.entry.select_range(start, end)
        self.entry.icursor(end)

    def on_ok(self):
        self.result = self.entry.get()
        self.destroy()


# --- ANA UYGULAMA ---

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SecureVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Korumalı Kasa (Vault) Yöneticisi")
        
        self.withdraw()
        
        pencere_g = 600
        pencere_h = 780
        
        self.geometry(f"{pencere_g}x{pencere_h}")
        self.resizable(False, False)

        self.update()
        
        scaling = self._get_window_scaling()
        
        scaled_g = int(pencere_g * scaling)
        scaled_h = int(pencere_h * scaling)
        
        ekran_g = self.winfo_screenwidth()
        ekran_h = self.winfo_screenheight()
        
        x = max(0, int((ekran_g - scaled_g) / 2))
        y = max(0, int((ekran_h - scaled_h) / 2))
        
        self.geometry(f"{pencere_g}x{pencere_h}+{x}+{y}")
        self.deiconify()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        if getattr(sys, 'frozen', False):
            self.current_dir = os.path.dirname(sys.executable)
        else:
            self.current_dir = os.path.dirname(os.path.abspath(__file__))

        self.vault_password = None
        self.current_vault_path = None
        self.current_relative_path = ""
        
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

        self.entry_pwd_confirm = ctk.CTkEntry(self.frame_login, placeholder_text="Şifreyi Tekrar Girin", show="*", width=300, height=40, font=("Arial", 14))

        self.btn_login = ctk.CTkButton(self.frame_login, text="Giriş Yap", width=300, height=45, font=("Arial", 15, "bold"), command=self.login_or_create_vault)
        self.btn_login.pack(pady=15)
        
        self.btn_refresh = ctk.CTkButton(self.frame_login, text="🔄 Klasörleri Yenile", fg_color="transparent", border_width=1, command=self.refresh_folders)
        self.btn_refresh.pack(pady=5)

    def show_login_frame(self):
        self.frame_vault.pack_forget()
        self.frame_login.pack(fill="both", expand=True)
        self.refresh_folders()

    def show_vault_frame(self):
        self.frame_login.pack_forget()
        self.frame_vault.pack(fill="both", expand=True)
        self.lbl_vault_name.configure(text=f"Açık Kasa: {os.path.basename(self.current_vault_path)}")
        self.refresh_vault_files()

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
                
                unencrypted_files = []
                for root, dirs, files in os.walk(folder_path):
                    if ".git" in root or "__pycache__" in root:
                        continue
                    for file in files:
                        if file == ".vault_check" or file.endswith(".enc"):
                            continue
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, folder_path)
                        unencrypted_files.append((file, full_path, rel_path))
                
                if unencrypted_files:
                    file_list_str = ", ".join([item[0] for item in unencrypted_files[:3]])
                    if len(unencrypted_files) > 3:
                        file_list_str += f" ve {len(unencrypted_files) - 3} dosya daha"
                        
                    confirm = CustomConfirmBox(
                        self,
                        "Şifrelenmemiş Dosyalar Tespit Edildi",
                        f"Kasada şifrelenmemiş dosyalar bulundu ({file_list_str}). Bu dosyaları otomatik olarak şifrelemek ister misiniz?",
                        "warning"
                    )
                    if confirm.result:
                        for file, file_path, rel_path in unencrypted_files:
                            target_path = file_path + ".enc"
                            if os.path.exists(target_path):
                                file_confirm = CustomConfirmBox(
                                    self,
                                    "Üzerine Yazma Onayı",
                                    f"'{rel_path}' dosyasının şifrelenmiş hali (.enc) zaten kasada mevcut. Üzerine yazmak istiyor musunuz?",
                                    "warning"
                                )
                                if not file_confirm.result:
                                    continue

                            try:
                                with open(file_path, "rb") as f:
                                    data = f.read()
                                enc_data = encrypt_bytes(data, pwd)
                                with open(target_path, "wb") as f:
                                    f.write(enc_data)
                                os.remove(file_path)
                            except Exception as e:
                                pass
                        CustomMessageBox(self, "Bilgi", "Şifrelenmemiş dosyalar işleme alındı.", "info")

                self.vault_password = pwd
                self.current_vault_path = folder_path
                self.current_relative_path = ""
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
                    
                unencrypted_files = []
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file == ".vault_check" or file.endswith(".enc"):
                            continue
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, folder_path)
                        unencrypted_files.append((file, full_path, rel_path))
                
                encrypt_existing = True
                if unencrypted_files:
                    file_list_str = ", ".join([item[0] for item in unencrypted_files[:3]])
                    if len(unencrypted_files) > 3:
                        file_list_str += f" ve {len(unencrypted_files) - 3} dosya daha"
                        
                    confirm = CustomConfirmBox(
                        self,
                        "Şifrelenmemiş Dosyalar Tespit Edildi",
                        f"Klasörde şifrelenmemiş dosyalar bulundu ({file_list_str}). Bu dosyaları otomatik olarak şifrelemek ister misiniz?",
                        "warning"
                    )
                    encrypt_existing = confirm.result

                if encrypt_existing and unencrypted_files:
                    for file, file_path, rel_path in unencrypted_files:
                        target_path = file_path + ".enc"
                        if os.path.exists(target_path):
                            file_confirm = CustomConfirmBox(
                                self,
                                "Üzerine Yazma Onayı",
                                f"'{rel_path}' dosyasının şifrelenmiş hali (.enc) zaten kasada mevcut. Üzerine yazmak istiyor musunuz?",
                                "warning"
                            )
                            if not file_confirm.result:
                                continue

                        try:
                            with open(file_path, "rb") as f:
                                data = f.read()
                            enc_data = encrypt_bytes(data, pwd)
                            with open(target_path, "wb") as f:
                                f.write(enc_data)
                            os.remove(file_path)
                        except Exception as e:
                            pass
                    CustomMessageBox(self, "Başarılı", "Kasa oluşturuldu ve mevcut dosyalar işlendi!", "info")
                else:
                    CustomMessageBox(self, "Başarılı", "Kasa oluşturuldu!", "info")

                self.vault_password = pwd
                self.current_vault_path = folder_path
                self.current_relative_path = ""
                self.entry_pwd.delete(0, 'end')
                self.entry_pwd_confirm.delete(0, 'end')
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

        self.scroll_files = ctk.CTkScrollableFrame(self.frame_vault, height=200, label_text="Kasadaki Dosyalar ve Klasörler")
        self.scroll_files.pack(fill="x", padx=20, pady=5)

        self.frame_vault_controls = ctk.CTkFrame(self.frame_vault, fg_color="transparent")
        self.frame_vault_controls.pack(fill="x", padx=20, pady=5)
        
        self.frame_vault_controls.grid_columnconfigure(0, weight=1)
        self.frame_vault_controls.grid_columnconfigure(1, weight=1)

        # 1. ve 2. satırların yer değiştirdiği buton sıralaması
        self.btn_rename = ctk.CTkButton(self.frame_vault_controls, text="✏️ Yeniden Adlandır", fg_color="#E67E22", hover_color="#D35400", command=self.rename_item_in_vault)
        self.btn_rename.grid(row=0, column=0, padx=5, pady=4, sticky="we")

        self.btn_new_folder = ctk.CTkButton(self.frame_vault_controls, text="📁 Yeni Klasör Oluştur", fg_color="#D35400", hover_color="#BA4A00", command=self.create_subfolder)
        self.btn_new_folder.grid(row=0, column=1, padx=5, pady=4, sticky="we")

        self.btn_export_file = ctk.CTkButton(self.frame_vault_controls, text="📤 Şifresiz Dışa Aktar", fg_color="#9B59B6", hover_color="#8E44AD", command=self.export_file_from_vault)
        self.btn_export_file.grid(row=1, column=0, padx=5, pady=4, sticky="we")

        self.btn_del_file = ctk.CTkButton(self.frame_vault_controls, text="🗑️ Seçileni Sil", fg_color="transparent", border_width=1, text_color="#E74C3C", border_color="#E74C3C", hover_color="#3A1C1C", command=self.delete_file_from_vault)
        self.btn_del_file.grid(row=1, column=1, padx=5, pady=4, sticky="we")

        self.btn_add_file = ctk.CTkButton(self.frame_vault_controls, text="➕ Kasaya Dosya Ekle", fg_color="#2FA572", hover_color="#1E6B49", command=self.add_file_to_vault)
        self.btn_add_file.grid(row=2, column=0, columnspan=2, padx=5, pady=4, sticky="we")

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
            current_full_path = os.path.join(self.current_vault_path, self.current_relative_path)
            
            if self.current_relative_path != "":
                btn_back = ctk.CTkButton(
                    self.scroll_files, text="📁 .. (Üst Klasöre Dön)", 
                    fg_color="transparent", text_color="#3498DB", 
                    anchor="w", hover_color="#333333",
                    command=self.go_back_folder
                )
                btn_back.pack(fill="x", pady=2, padx=5)

            items = os.listdir(current_full_path)
            folders = sorted([f for f in items if os.path.isdir(os.path.join(current_full_path, f)) and not f.startswith('.')])
            files = sorted([f for f in items if f.endswith('.enc') and os.path.isfile(os.path.join(current_full_path, f))])
            
            if not folders and not files and self.current_relative_path == "":
                lbl = ctk.CTkLabel(self.scroll_files, text="Kasa boş.", text_color="gray")
                lbl.pack(pady=20)
                return
                
            for folder in folders:
                rel_folder_path = os.path.join(self.current_relative_path, folder) if self.current_relative_path else folder
                
                row_frame = ctk.CTkFrame(self.scroll_files, fg_color="transparent")
                row_frame.pack(fill="x", pady=2, padx=5)
                
                rb = ctk.CTkRadioButton(
                    row_frame, text="", value=rel_folder_path, variable=self.radio_var,
                    width=20, fg_color="#F39C12"
                )
                rb.pack(side="left", padx=(0, 5))
                
                btn_folder = ctk.CTkButton(
                    row_frame, text=f"📁 {folder}/", 
                    fg_color="transparent", text_color="#F39C12", 
                    anchor="w", hover_color="#333333",
                    command=lambda f=folder: self.enter_folder(f)
                )
                btn_folder.pack(side="left", fill="x", expand=True)

            for file in files:
                display_name = file[:-4]
                rel_file_path = os.path.join(self.current_relative_path, file) if self.current_relative_path else file
                
                row_frame = ctk.CTkFrame(self.scroll_files, fg_color="transparent")
                row_frame.pack(fill="x", pady=2, padx=5)
                
                rb = ctk.CTkRadioButton(
                    row_frame, text="", value=rel_file_path, variable=self.radio_var,
                    width=20, fg_color="#3498DB"
                )
                rb.pack(side="left", padx=(0, 5))
                
                btn_file = ctk.CTkButton(
                    row_frame, text=f"📄 {display_name}", 
                    fg_color="transparent", text_color="white", 
                    anchor="w", hover_color="#333333",
                    command=lambda p=rel_file_path: self.quick_open_file(p)
                )
                btn_file.pack(side="left", fill="x", expand=True)
        except Exception as e:
            pass

    def quick_open_file(self, file_path):
        self.radio_var.set(file_path)
        self.open_file_from_vault()

    def enter_folder(self, folder_name):
        if self.current_relative_path:
            self.current_relative_path = os.path.join(self.current_relative_path, folder_name)
        else:
            self.current_relative_path = folder_name
        self.refresh_vault_files()

    def go_back_folder(self):
        parent = os.path.dirname(self.current_relative_path)
        self.current_relative_path = parent if parent else ""
        self.refresh_vault_files()

    def create_subfolder(self):
        dialog = CustomInputDialog(self, title="Klasör Oluştur", text="Yeni klasör adını girin:")
        folder_name = dialog.result
        if not folder_name: return
            
        folder_name = folder_name.strip()
        if not folder_name: return
            
        current_full_path = os.path.join(self.current_vault_path, self.current_relative_path)
        new_folder_path = os.path.join(current_full_path, folder_name)
        
        if os.path.exists(new_folder_path):
            CustomMessageBox(self, "Hata", "Bu isimde bir klasör veya dosya zaten var!", "error")
            return
            
        try:
            os.makedirs(new_folder_path)
            CustomMessageBox(self, "Başarılı", f"'{folder_name}' klasörü oluşturuldu.", "info")
            self.refresh_vault_files()
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Klasör oluşturulamadı:\n{e}", "error")

    def add_file_to_vault(self):
        file_paths = filedialog.askopenfilenames(title="Kasaya Eklenecek Dosyaları Seçin")
        if not file_paths: return
        
        current_target_dir = os.path.join(self.current_vault_path, self.current_relative_path)
        
        try:
            added_count = 0
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                target_path = os.path.join(current_target_dir, file_name + ".enc")
                
                if os.path.exists(target_path):
                    confirm = CustomConfirmBox(
                        self,
                        "Üzerine Yazma Onayı",
                        f"'{file_name}' adında bir dosya zaten bu klasörde mevcut. Üzerine yazmak istiyor musunuz?",
                        "warning"
                    )
                    if not confirm.result:
                        continue
                
                with open(file_path, "rb") as f:
                    data = f.read()
                
                enc_data = encrypt_bytes(data, self.vault_password)
                with open(target_path, "wb") as f:
                    f.write(enc_data)
                added_count += 1
                
            if added_count > 0:
                CustomMessageBox(self, "Başarılı", "Dosyalar şifrelenerek kasaya eklendi.", "info")
                self.refresh_vault_files()
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Dosya eklenirken hata:\n{e}", "error")

    def open_file_from_vault(self):
        if self.active_temp_file:
            CustomMessageBox(self, "Uyarı", "Önce açık olan dosyayı kapatmalısınız!", "warning")
            return
            
        selected_file_rel = self.radio_var.get()
        if not selected_file_rel:
            CustomMessageBox(self, "Uyarı", "Lütfen açmak için bir dosya seçin.", "warning")
            return

        enc_file_path = os.path.join(self.current_vault_path, selected_file_rel)
        if os.path.isdir(enc_file_path):
            CustomMessageBox(self, "Uyarı", "Klasörler açılamaz. Lütfen bir dosya seçin.", "warning")
            return

        original_name = os.path.basename(selected_file_rel)[:-4]
        
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

            self.lbl_active_filename.configure(text=f"Açık Dosya: {selected_file_rel[:-4]}")
            self.frame_active.pack(fill="x", padx=20, pady=5)
            
        except Exception as e:
            self.active_temp_file = None
            self.active_vault_file = None
            CustomMessageBox(self, "Hata", f"Dosya açılamadı:\n{e}", "error")

    def save_and_close_active_file(self):
        if not self.active_temp_file or not self.active_vault_file:
            return
            
        try:
            with open(self.active_temp_file, "rb") as f:
                new_data = f.read()
            
            enc_data = encrypt_bytes(new_data, self.vault_password)
            with open(self.active_vault_file, "wb") as f:
                f.write(enc_data)
                
            if os.path.exists(self.active_temp_file):
                os.remove(self.active_temp_file)
                
            self.active_temp_file = None
            self.active_vault_file = None
            self.frame_active.pack_forget()
            CustomMessageBox(self, "Başarılı", "Değişiklikler kaydedildi ve geçici dosya temizlendi.", "info")
            self.refresh_vault_files()
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Kaydedilirken hata oluştu:\n{e}", "error")

    def close_without_saving_active_file(self):
        if self.active_temp_file and os.path.exists(self.active_temp_file):
            try:
                os.remove(self.active_temp_file)
            except Exception:
                pass
        self.active_temp_file = None
        self.active_vault_file = None
        self.frame_active.pack_forget()
        CustomMessageBox(self, "Bilgi", "Değişiklikler kaydedilmeden kapatıldı.", "info")

    def export_file_from_vault(self):
        selected_file_rel = self.radio_var.get()
        if not selected_file_rel:
            CustomMessageBox(self, "Uyarı", "Lütfen dışa aktarmak için bir dosya seçin.", "warning")
            return

        enc_file_path = os.path.join(self.current_vault_path, selected_file_rel)
        if os.path.isdir(enc_file_path):
            CustomMessageBox(self, "Uyarı", "Klasörler dışa aktarılamaz.", "warning")
            return

        original_name = os.path.basename(selected_file_rel)[:-4]
        save_path = filedialog.asksaveasfilename(title="Dosyayı Kaydet", initialfile=original_name)
        if not save_path:
            return

        try:
            with open(enc_file_path, "rb") as f:
                enc_data = f.read()
            dec_data = decrypt_bytes(enc_data, self.vault_password)
            with open(save_path, "wb") as f:
                f.write(dec_data)
            CustomMessageBox(self, "Başarılı", "Dosya başarıyla şifresiz olarak dışa aktarıldı.", "info")
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Dışa aktarma hatası:\n{e}", "error")

    def delete_file_from_vault(self):
        selected_file_rel = self.radio_var.get()
        if not selected_file_rel:
            CustomMessageBox(self, "Uyarı", "Lütfen silmek için bir öge seçin.", "warning")
            return

        target_path = os.path.join(self.current_vault_path, selected_file_rel)
        is_dir = os.path.isdir(target_path)
        item_type = "klasörü" if is_dir else "dosyasını"

        confirm = CustomConfirmBox(
            self,
            "Silme Onayı",
            f"'{os.path.basename(selected_file_rel)}' {item_type} silmek istediğinize emin misiniz?",
            "error"
        )
        if confirm.result:
            try:
                if is_dir:
                    shutil.rmtree(target_path)
                else:
                    os.remove(target_path)
                CustomMessageBox(self, "Başarılı", "Öge silindi.", "info")
                self.refresh_vault_files()
            except Exception as e:
                CustomMessageBox(self, "Hata", f"Silme hatası:\n{e}", "error")

    def rename_item_in_vault(self):
        selected_file_rel = self.radio_var.get()
        if not selected_file_rel:
            CustomMessageBox(self, "Uyarı", "Lütfen yeniden adlandırmak için bir öge seçin.", "warning")
            return

        target_path = os.path.join(self.current_vault_path, selected_file_rel)
        is_dir = os.path.isdir(target_path)
        old_name = os.path.basename(selected_file_rel)
        
        if not is_dir and old_name.endswith('.enc'):
            old_display_name = old_name[:-4]
            ext = os.path.splitext(old_display_name)[1]
            ext_len = len(ext)
        else:
            old_display_name = old_name
            ext_len = 0

        dialog = CustomInputDialog(
            self,
            title="Yeniden Adlandır",
            text="Yeni ismi girin:",
            initial_value=old_display_name,
            select_to_ext=True,
            ext_length=ext_len
        )
        new_name = dialog.result
        if not new_name or new_name == old_display_name:
            return

        new_name = new_name.strip()
        if not is_dir:
            new_file_name = new_name + ".enc"
        else:
            new_file_name = new_name

        parent_dir = os.path.dirname(target_path)
        new_path = os.path.join(parent_dir, new_file_name)

        if os.path.exists(new_path):
            CustomMessageBox(self, "Hata", "Bu isimde bir dosya/klasör zaten var!", "error")
            return

        try:
            os.rename(target_path, new_path)
            CustomMessageBox(self, "Başarılı", "Yeniden adlandırıldı.", "info")
            self.refresh_vault_files()
        except Exception as e:
            CustomMessageBox(self, "Hata", f"Yeniden adlandırma hatası:\n{e}", "error")

    def logout(self):
        if self.active_temp_file and os.path.exists(self.active_temp_file):
            try:
                os.remove(self.active_temp_file)
            except Exception:
                pass
        self.active_temp_file = None
        self.active_vault_file = None
        self.vault_password = None
        self.current_vault_path = None
        self.current_relative_path = ""
        self.frame_active.pack_forget()
        self.show_login_frame()

    def on_closing(self):
        if self.active_temp_file and os.path.exists(self.active_temp_file):
            try:
                os.remove(self.active_temp_file)
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    app = SecureVaultApp()
    app.mainloop()