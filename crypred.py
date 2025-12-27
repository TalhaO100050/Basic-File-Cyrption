import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend


def _derive_key(password: str, salt: bytes) -> bytes:
    """Şifreyi Fernet anahtarına dönüştürür"""
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

while True:

    #Decryping or Encrypting Menu
    while True:
        menu =  input("1 - Decrypting\n2 - Encrypting\n")
        menu = int(menu)
        if menu == 1 or menu == 2:
            break

    #Decryping
    if menu == 1:
        menu = 0

        #Yazı Çevirme or Dosya Çevirme Menu
        while True:
            menu = input("1 - Yazı çevirme(kullanma)\n2 - Dosya çevirme\n")
            menu = int(menu)
            if menu == 1 or menu == 2:
                break

        #Yazı Çevirme
        if menu == 1:
            menu = 0
            dosya = input("Çevireceğiniz yazıyı giriniz.\n")
            sifre = input("Şifreyi giriniz.\n")

            decrypted_dosya = decrypt_bytes(dosya, sifre)

            try:
                decrypted_dosya = decrypted_dosya.decode("utf-8")
            except UnicodeDecodeError:
                pass

            #Print or Create File Menu 
            while True:
                menu = input("1 - Oku\n2 - Dosya oluştur\n")
                menu = int(menu)
                if menu == 1 or menu == 2:
                    break

            #Print
            if menu == 1:
                menu = 0
                print(decrypted_dosya)

            #Create File
            if menu == 2:
                menu = 0
                path = input("Oluşturulacak dosyanın uzantısını giriniz.\nEğer dosya aynı klasördeyse '.' yazınız.\n")
                dosya_adi_yazma = input("Oluşturulacak dosyanın adını giriniz.\n")

                icerik = decrypted_dosya

                with open(os.path.join(path, dosya_adi_yazma), "x") as f:
                    f.write(icerik)

        #Dosya Çevirme
        if menu == 2:
            menu = 0
            path = input("Dosya uzantısı giriniz.\nEğer dosya aynı klasördeyse '.' yazınız.\n")
            dosya_adi = input("Dosyanın adını giriniz.\n")
            sifre = input("Şifreyi giriniz.\n")

            with open(os.path.join(path, dosya_adi), "rb") as f:
                dosya = f.read()

            decrypted_dosya = decrypt_bytes(dosya, sifre)

            try:
                decrypted_dosya = decrypted_dosya.decode("utf-8")
            except UnicodeDecodeError:
                pass

            #Print or Create File Menu 
            while True:
                menu = input("1 - Oku\n2 - Dosya oluştur\n")
                menu = int(menu)
                if menu == 1 or menu == 2:
                    break

            #Print
            if menu == 1:
                menu = 0
                print(decrypted_dosya)

            #Create File
            if menu == 2:
                menu = 0
                path = input("Oluşturulacak dosyanın uzantısını giriniz.\nEğer dosya aynı klasördeyse '.' yazınız.\n")
                dosya_adi_yazma = input("Oluşturulacak dosyanın adını giriniz.\n")

                icerik = decrypted_dosya

                if isinstance(icerik, bytes):
                    mode = "xb"
                else:
                    mode = "x"

                with open(os.path.join(path, dosya_adi_yazma), mode, encoding="utf-8" if mode == "x" else None) as f:
                    f.write(icerik)
    
    #Encrypting
    if menu == 2:
        menu = 0

        #Yazı Şifreleme or Dosya Şifreleme Menu
        while True:
            menu = input("1 - Yazı şifreleme\n2 - Dosya şifreleme\n")
            menu = int(menu)
            if menu == 1 or menu == 2:
                break

        #Yazı Şifreleme
        if menu == 1:
            menu = 0
            dosya = input("Şifreliyeceğiniz yazıyı giriniz.\n")
            sifre = input("Şifre giriniz.\n")

            if isinstance(dosya, str):
                dosya = dosya.encode("utf-8")

            encrypted_dosya = encrypt_bytes(dosya, sifre)

            #Print or Create File Menu 
            while True:
                menu = input("1 - Oku(Kullanma)\n2 - Dosya oluştur\n")
                menu = int(menu)
                if menu == 1 or menu == 2:
                    break

            #Print
            if menu == 1:
                menu = 0
                print(encrypted_dosya)

            #Create File
            if menu == 2:
                menu = 0
                path = input("Oluşturulacak dosyanın uzantısını giriniz.\nEğer dosya aynı klasördeyse '.' yazınız.\n")
                dosya_adi_yazma = input("Oluşturulacak dosyanın adını giriniz.\n")

                icerik = encrypted_dosya

                with open(os.path.join(path, dosya_adi_yazma), "xb") as f:
                    f.write(icerik)

        #Dosya Şifreleme
        if menu == 2:
            menu = 0
            path = input("Dosya uzantısı giriniz.\nEğer dosya aynı klasördeyse '.' yazınız.\n")
            dosya_adi = input("Dosyanın adını giriniz.\n")
            sifre = input("Şifre giriniz.\n")

            with open(os.path.join(path, dosya_adi), "rb") as f:
                dosya = f.read()

            if isinstance(dosya, str):
                dosya = dosya.encode("utf-8")

            encrypted_dosya = encrypt_bytes(dosya, sifre)


            #Print or Create File Menu 
            while True:
                menu = input("1 - Oku(Kullanma)\n2 - Dosya oluştur\n")
                menu = int(menu)
                if menu == 1 or menu == 2:
                    break

            #Print
            if menu == 1:
                menu = 0
                print(encrypted_dosya)

            #Create File
            if menu == 2:
                menu = 0
                path = input("Oluşturulacak dosyanın uzantısını giriniz.\nEğer dosya aynı klasördeyse '.' yazınız.\n")
                dosya_adi_yazma = input("Oluşturulacak dosyanın adını giriniz.\n")

                icerik = encrypted_dosya

                with open(os.path.join(path, dosya_adi_yazma), "xb") as f:
                    f.write(icerik)

        


    