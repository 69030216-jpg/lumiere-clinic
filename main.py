"""Beauty Clinic — Python 3 / Tkinter / MySQL. Open this file in Thonny."""
from pathlib import Path
import sys
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'vendor'))
VERSION_VENDOR=BASE/f'vendor_py{sys.version_info.major}{sys.version_info.minor}'
if VERSION_VENDOR.is_dir():
    sys.path.insert(0,str(VERSION_VENDOR))
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import hashlib
import secrets
import hmac
import re
import calendar
import threading
import queue
from fractions import Fraction
from tkinter import font as tkfont
from datetime import datetime, date, timedelta
from functools import wraps

WHITE, CREAM, GOLD, INK = '#FFFFFF', '#FBF9F5', '#B99452', '#35312C'
UI_FONT = 'Leelawadee UI'
ROLES = {'ผู้รับบริการ': 'customer', 'ผู้ดูแลระบบ': 'admin', 'แพทย์': 'doctor'}
STATUS = {'pending': 'รออนุมัติ', 'approved': 'อนุมัติแล้ว', 'confirmed': 'ยืนยันการนัด',
          'in_progress': 'กำลังรับบริการ', 'completed': 'รับบริการสำเร็จ', 'cancelled': 'ยกเลิก'}


def booking_day_allowed(value, today=None):
    return value >= (today or date.today()) and value.weekday() != 2


def next_booking_day(value):
    while not booking_day_allowed(value):
        value += timedelta(days=1)
    return value


def treatment_asset(name):
    text = name.casefold()
    for words, asset in [(('botox','โบท็อก'),'botox'),(('filler','ฟิลเลอร์'),'filler'),
                         (('ultraformer','ยกกระชับ'),'ultraformer'),(('จมูก',),'rhinoplasty'),
                         (('หน้าอก',),'breast')]:
        if any(word in text for word in words):
            return asset+'.png'
    return 'clinic_lounge.png'


class ClinicImage(tk.Canvas):
    """Offline project artwork, scaled on resize. Pillow is optional."""
    def __init__(self, parent, height=130, title='A MOMENT FOR YOURSELF', caption='Lumiére Clinic  /  BEAUTY & WELLNESS', asset='clinic_lounge.png', overlay=True, natural_ratio=False, **kwargs):
        super().__init__(parent, height=height, bg='#F0E9DF', highlightthickness=0, **kwargs)
        self.heading, self.caption, self.source, self.photo = title, caption, None, None
        self.native_source = None
        self.overlay = overlay
        self.natural_ratio=natural_ratio
        self.set_asset(asset)
        self.bind('<Configure>', self.draw)

    def set_asset(self, asset):
        path = BASE / 'assets' / asset
        if not path.exists():
            path = BASE / 'assets' / 'clinic_lounge.png'
        self.source = None
        self.native_source = None
        self.photo = None
        try:
            from PIL import Image, ImageOps, ImageTk
            self.image_tools = Image, ImageOps, ImageTk
            with Image.open(path) as image:
                self.source = image.convert('RGB')
        except (ImportError, OSError):
            try:
                self.native_source = tk.PhotoImage(file=str(path))
            except tk.TclError:
                pass
        if self.winfo_width()>1:
            self.draw()

    def draw(self, event=None):
        width, height = max(self.winfo_width(), 1), max(self.winfo_height(), 1)
        if self.natural_ratio and width>1:
            sw,sh=(self.source.size if self.source else (self.native_source.width(),self.native_source.height()) if self.native_source else (3,2))
            expected=max(120,round(width*sh/sw))
            if int(self.cget('height'))!=expected:
                self.configure(height=expected)
        self.delete('all')
        if self.source:
            Image, ImageOps, ImageTk = self.image_tools
            resized = (ImageOps.fit(self.source,(width,height),Image.Resampling.LANCZOS) if self.overlay
                       else ImageOps.contain(self.source,(width,height),Image.Resampling.LANCZOS))
            self.photo = ImageTk.PhotoImage(resized)
        elif self.native_source:
            # Thonny may use another Python version than the bundled Pillow binary.
            # Resize with Tk itself instead of drawing the original at full size.
            sw,sh=self.native_source.width(),self.native_source.height()
            ratio=(max if self.overlay else min)(width/sw,height/sh)
            factor=Fraction(ratio).limit_denominator(32)
            numerator=max(1,factor.numerator)
            denominator=max(1,factor.denominator)
            self.photo=self.native_source.subsample(denominator,denominator).zoom(numerator,numerator)
        if self.photo:
            self.create_image(width/2,height/2,image=self.photo,anchor='center')
        if not self.overlay:
            return
        if height > 260:
            self.create_rectangle(24,height-170,width-24,height-24,fill='#F9F5EE',outline='')
            self.create_text(45,height-140,text='Lumiére Clinic',font=('Georgia',28),fill=GOLD,anchor='nw')
            self.create_text(45,height-86,text='พื้นที่แห่งความงามและการดูแลคุณ',font=(UI_FONT,13),fill=INK,anchor='nw',width=max(120,width-90))
        else:
            panel = min(width, max(330, int(width*.49)))
            self.create_rectangle(0,0,panel,height,fill='#F6F1E9',outline='')
            self.create_rectangle(0,0,4,height,fill=GOLD,outline='')
            self.create_text(22, height*.32,text=self.caption,font=(UI_FONT,9),fill='#8C7754',anchor='w',width=max(100,panel-35))
            self.create_text(22,height*.67,text=self.heading,font=('Georgia',17),fill=INK,anchor='w',width=max(100,panel-35))


class BookingCalendar(tk.Toplevel):
    MONTHS = ('มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน',
              'กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม')

    def __init__(self, parent, selected, on_select):
        super().__init__(parent)
        self.title('เลือกวันนัดหมาย')
        self.geometry('470x450')
        self.resizable(False,False)
        self.configure(bg=WHITE)
        self.transient(parent)
        self.grab_set()
        self.selected, self.on_select = selected, on_select
        self.month = max(selected, date.today()).replace(day=1)
        self.day_buttons = {}
        self.render()

    def move(self, delta):
        value = self.month.year*12+self.month.month-1+delta
        new = date(value//12,value%12+1,1)
        if new >= date.today().replace(day=1):
            self.month = new
            self.render()

    def choose(self, value):
        if not booking_day_allowed(value):
            return
        self.on_select(value)
        self.destroy()

    def render(self):
        for child in self.winfo_children():
            child.destroy()
        self.day_buttons = {}
        header = tk.Frame(self,bg=WHITE)
        header.pack(fill='x',padx=20,pady=16)
        ttk.Button(header,text='‹',width=3,command=lambda:self.move(-1),
                   state='normal' if self.month>date.today().replace(day=1) else 'disabled').pack(side='left')
        tk.Label(header,text=f'{self.MONTHS[self.month.month-1]} {self.month.year+543}',
                 font=(UI_FONT,16,'normal'),bg=WHITE,fg=GOLD).pack(side='left',expand=True)
        ttk.Button(header,text='›',width=3,command=lambda:self.move(1)).pack(side='right')
        grid = tk.Frame(self,bg=WHITE)
        grid.pack(fill='both',expand=True,padx=20)
        for col,label in enumerate(('จ.','อ.','พ.','พฤ.','ศ.','ส.','อา.')):
            grid.columnconfigure(col,weight=1)
            tk.Label(grid,text=label,bg=WHITE,fg='#B4A38E' if col==2 else INK,font=(UI_FONT,11)).grid(row=0,column=col,pady=7)
        for r,week in enumerate(calendar.monthcalendar(self.month.year,self.month.month),1):
            grid.rowconfigure(r,weight=1)
            for c,num in enumerate(week):
                if not num:
                    continue
                value = self.month.replace(day=num)
                allowed = booking_day_allowed(value)
                button = tk.Button(grid,text=str(num),font=(UI_FONT,12),relief='flat',borderwidth=0,
                    bg=GOLD if value==self.selected and allowed else '#F7F3EC' if allowed else '#F5F5F5',
                    fg=WHITE if value==self.selected and allowed else INK,disabledforeground='#C5C5C5',
                    activebackground='#E7D9BC',state='normal' if allowed else 'disabled',
                    command=lambda d=value:self.choose(d))
                button.grid(row=r,column=c,sticky='nsew',padx=3,pady=3)
                self.day_buttons[value]=button
        tk.Label(self,text='คลินิกหยุดทุกวันพุธ • วันที่สีจางไม่สามารถเลือกได้',
                 bg=WHITE,fg='#8C7754',font=(UI_FONT,10)).pack(pady=16)


def password_hash(value):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), 260000).hex()
    return salt + ':' + digest


def password_ok(value, stored):
    try:
        salt, digest = stored.split(':')
        actual = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), 260000).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, AttributeError):
        return False


def strong_password(value):
    if len(value) < 8:
        raise ValueError('รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร')


def safe(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            messagebox.showerror('ไม่สามารถดำเนินการได้', str(exc))
    return wrapped


class Database:
    def __init__(self, config):
        try:
            import mysql.connector as connector
        except ImportError:
            raise ValueError('ยังไม่มี mysql-connector-python\nติดตั้งผ่าน Tools > Manage packages ใน Thonny')
        self.connector, self.config = connector, config
        self.initialize()

    def connect(self, server_only=False):
        args = dict(host=self.config['host'], user=self.config['user'],
                    password=self.config['password'], port=int(self.config['port']),
                    connection_timeout=5, charset='utf8mb4')
        if not server_only:
            args['database'] = self.config['database']
        return self.connector.connect(**args)

    def query(self, sql, params=(), one=False):
        conn = self.connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, params)
            result = cur.fetchall() if cur.with_rows else cur.lastrowid
            conn.commit()
            return (result[0] if result else None) if one else result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def authenticate(self, username, password):
        username = username.strip()
        if not username or not password:
            raise ValueError('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน')
        user = self.query('SELECT * FROM users WHERE LOWER(username)=LOWER(%s)',(username,),one=True)
        if not user or not password_ok(password,user['password_hash']):
            raise ValueError('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบตัวพิมพ์ของรหัสผ่าน')
        if user['role']=='doctor' and not self.query('SELECT id FROM doctors WHERE user_id=%s AND active=1',(user['id'],),one=True):
            raise ValueError('บัญชีแพทย์นี้ปิดใช้งานแล้ว กรุณาติดต่อผู้ดูแลระบบ')
        return user

    def initialize(self):
        name = self.config['database']
        if not name or len(name) > 64 or any(c in name for c in '`/\\\x00'):
            raise ValueError('ชื่อฐานข้อมูลไม่ถูกต้อง')
        conn = self.connect(True)
        try:
            cur = conn.cursor()
            cur.execute(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
            cur.execute(f'USE `{name}`')
            definitions = [
                """CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(80) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL, role ENUM('customer','admin','doctor') NOT NULL,
                    full_name VARCHAR(150) NOT NULL, phone VARCHAR(30) NOT NULL,
                    security_question VARCHAR(255) NOT NULL, security_answer VARCHAR(255) NOT NULL,
                    points INT NOT NULL DEFAULT 0) ENGINE=InnoDB""",
                """CREATE TABLE IF NOT EXISTS doctors (
                    id INT AUTO_INCREMENT PRIMARY KEY, user_id INT UNIQUE NOT NULL,
                    specialty VARCHAR(200) NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE,
                    FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB""",
                """CREATE TABLE IF NOT EXISTS treatments (
                    id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(150) NOT NULL,
                    description TEXT NOT NULL, benefits TEXT NOT NULL, recovery TEXT NOT NULL,
                    price DECIMAL(12,2) NOT NULL, duration INT NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE)
                    ENGINE=InnoDB""",
                """CREATE TABLE IF NOT EXISTS bookings (
                    id INT AUTO_INCREMENT PRIMARY KEY, customer_id INT NOT NULL, doctor_id INT NOT NULL,
                    treatment_id INT NOT NULL, starts_at DATETIME NOT NULL, ends_at DATETIME NOT NULL,
                    price DECIMAL(12,2) NOT NULL, treatment_name VARCHAR(150) NOT NULL,
                    status ENUM('pending','approved','confirmed','in_progress','completed','cancelled')
                    NOT NULL DEFAULT 'pending', doctor_notes TEXT, post_care TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(customer_id) REFERENCES users(id),
                    FOREIGN KEY(doctor_id) REFERENCES doctors(id),
                    FOREIGN KEY(treatment_id) REFERENCES treatments(id),
                    INDEX schedule_idx(doctor_id,starts_at,ends_at)) ENGINE=InnoDB""",
                """CREATE TABLE IF NOT EXISTS dispatches (
                    id INT AUTO_INCREMENT PRIMARY KEY, booking_id INT NOT NULL, admin_id INT NOT NULL,
                    note TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(booking_id) REFERENCES bookings(id),
                    FOREIGN KEY(admin_id) REFERENCES users(id)) ENGINE=InnoDB""",
                """CREATE TABLE IF NOT EXISTS app_meta (
                    meta_key VARCHAR(80) PRIMARY KEY, meta_value VARCHAR(255)) ENGINE=InnoDB"""
            ]
            for sql in definitions:
                cur.execute(sql)
            conn.commit()
            # A named lock makes first-run seeding safe across multiple app instances.
            cur.execute("SELECT GET_LOCK('beauty_clinic_seed',10)")
            if cur.fetchone()[0] != 1:
                raise ValueError('กำลังสร้างข้อมูลเริ่มต้น กรุณาลองใหม่')
            try:
                cur.execute("SELECT meta_value FROM app_meta WHERE meta_key='seed_v1'")
                if not cur.fetchone():
                    self.seed(cur)
                    conn.commit()
            finally:
                cur.execute("SELECT RELEASE_LOCK('beauty_clinic_seed')")
                cur.fetchone()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def seed(self, cur):
        users = [('admin', 'admin', 'ผู้ดูแลคลินิก'), ('customer', 'customer', 'คุณลูกค้าทดลอง'),
                 ('doctor1', 'doctor', 'พญ. พิมพ์ชนก'), ('doctor2', 'doctor', 'นพ. ธนกฤต'),
                 ('doctor3', 'doctor', 'พญ. อริสา')]
        for username, role, name in users:
            cur.execute('SELECT id FROM users WHERE username=%s', (username,))
            existing = cur.fetchone()
            if existing:
                raise ValueError('มีบัญชีชื่อเดียวกับข้อมูลตัวอย่าง กรุณาใช้ฐานข้อมูลใหม่สำหรับโปรเจกต์นี้')
            cur.execute('''INSERT INTO users(username,password_hash,role,full_name,phone,
                security_question,security_answer) VALUES(%s,%s,%s,%s,%s,%s,%s)''',
                (username, password_hash('Demo12345'), role, name, '0812345678',
                 'ชื่อสัตว์เลี้ยงตัวแรกของคุณ?', password_hash('beauty')))
            if role == 'doctor':
                cur.execute('INSERT INTO doctors(user_id,specialty) VALUES(%s,%s)',
                            (cur.lastrowid, 'เวชศาสตร์ความงาม' if username != 'doctor2' else 'ศัลยกรรมตกแต่ง'))
        treatments = [
            ('โบท็อก (Botox)', 'ฉีดสารเพื่อลดการทำงานของกล้ามเนื้อบางส่วน ต้องให้แพทย์ประเมิน',
             'อาจช่วยลดริ้วรอยจากการแสดงสีหน้า ผลลัพธ์แตกต่างกัน', 'อาจมีรอยช้ำหรือบวม ควรทำตามคำแนะนำแพทย์', 4990, 30),
            ('ฟิลเลอร์ (Filler)', 'การฉีดสารเติมเต็มเพื่อแก้ไขรูปทรงหรือร่องลึก',
             'ช่วยเพิ่มปริมาตรเฉพาะจุดตามความเหมาะสม', 'อาจบวมช้ำ มีความเสี่ยงหลอดเลือดอุดตัน ต้องประเมินกับแพทย์', 12900, 60),
            ('Ultraformer ยกกระชับ', 'ใช้พลังงานอัลตราซาวนด์เพื่อการยกกระชับตามข้อบ่งชี้',
             'อาจช่วยให้ผิวกระชับ ผลไม่เท่ากับการผ่าตัด', 'อาจปวด บวม หรือชา ตามการประเมินแพทย์', 15900, 60),
            ('เสริมจมูก', 'ผ่าตัดปรับรูปทรงจมูก ต้องปรึกษาศัลยแพทย์ก่อนนัดจริง',
             'ปรับรูปทรงตามโครงสร้างและความเหมาะสมเฉพาะบุคคล', 'มักต้องพักฟื้นหลายสัปดาห์ มีความเสี่ยงติดเชื้อและภาวะแทรกซ้อน', 35000, 120),
            ('เสริมหน้าอก', 'ผ่าตัดเพิ่มขนาดหน้าอก ต้องตรวจประเมินและเตรียมตัวก่อนผ่าตัด',
             'ปรับขนาดและรูปทรงตามความเหมาะสม', 'พักฟื้นหลายสัปดาห์หรือมากกว่า ต้องติดตามผลตามแพทย์นัด', 89000, 180)
        ]
        cur.executemany('''INSERT INTO treatments(name,description,benefits,recovery,price,duration)
            VALUES(%s,%s,%s,%s,%s,%s)''', treatments)
        cur.execute("INSERT INTO app_meta VALUES('seed_v1','done')")

    def book(self, customer_id, doctor_id, treatment_id, start):
        if not booking_day_allowed(start.date()):
            raise ValueError('ไม่สามารถจองวันย้อนหลังหรือวันพุธได้ คลินิกหยุดทุกวันพุธ')
        conn = self.connect()
        try:
            conn.start_transaction(isolation_level='READ COMMITTED')
            cur = conn.cursor(dictionary=True)
            # Lock customer then doctor: serializes overlapping reservations, including other PCs.
            cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE', (customer_id,))
            cur.fetchone()
            cur.execute('SELECT id FROM doctors WHERE id=%s AND active=1 FOR UPDATE', (doctor_id,))
            if not cur.fetchone():
                raise ValueError('แพทย์นี้ไม่เปิดรับจองแล้ว')
            cur.execute('SELECT * FROM treatments WHERE id=%s AND active=1 FOR UPDATE', (treatment_id,))
            treatment = cur.fetchone()
            if not treatment:
                raise ValueError('หัตถการนี้ไม่เปิดรับจองแล้ว')
            end = start + timedelta(minutes=treatment['duration'])
            if start <= datetime.now() or start.hour < 9 or end > start.replace(hour=18, minute=0):
                raise ValueError('เลือกเวลาในอนาคต โดยต้องทำเสร็จภายในเวลาทำการ 09:00–18:00')
            cur.execute('''SELECT id FROM bookings WHERE (doctor_id=%s OR customer_id=%s)
                AND status<>'cancelled' AND starts_at<%s AND ends_at>%s LIMIT 1''',
                (doctor_id, customer_id, end, start))
            if cur.fetchone():
                raise ValueError('เวลานี้แพทย์หรือคุณมีคิวอยู่แล้ว กรุณาเลือกเวลาอื่น')
            cur.execute('''INSERT INTO bookings(customer_id,doctor_id,treatment_id,starts_at,ends_at,
                price,treatment_name) VALUES(%s,%s,%s,%s,%s,%s,%s)''',
                (customer_id, doctor_id, treatment_id, start, end, treatment['price'], treatment['name']))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def transition(self, user, booking_id, target, notes='', care=''):
        conn = self.connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute('''SELECT b.*,d.user_id AS doctor_user FROM bookings b
                JOIN doctors d ON b.doctor_id=d.id WHERE b.id=%s FOR UPDATE''', (booking_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError('ไม่พบคิว')
            old, role = row['status'], user['role']
            allowed = False
            if role == 'admin':
                allowed = target in {'pending': ['approved','cancelled'],
                    'approved': ['confirmed','cancelled'], 'confirmed': ['cancelled']}.get(old, [])
            elif role == 'customer':
                allowed = row['customer_id'] == user['id'] and target == 'cancelled' and old in ('pending','approved','confirmed') and row['starts_at'] > datetime.now()
            elif role == 'doctor' and row['doctor_user'] == user['id']:
                allowed = (target=='approved' and old=='pending') or (target=='confirmed' and old=='approved') or (target == 'in_progress' and old in ('approved','confirmed')
                           and row['starts_at'].date() == date.today()) or (target == 'completed' and old == 'in_progress')
            if not allowed:
                raise ValueError('สิทธิ์หรือสถานะปัจจุบันไม่อนุญาตให้ทำรายการนี้ กรุณารีเฟรชข้อมูล')
            if target == 'completed' and not notes.strip():
                raise ValueError('กรุณาบันทึกการรักษาก่อนเสร็จสิ้น')
            if role == 'doctor' and target in ('in_progress','completed'):
                cur.execute('UPDATE bookings SET status=%s,doctor_notes=%s,post_care=%s WHERE id=%s',
                            (target, notes, care, booking_id))
            else:
                cur.execute('UPDATE bookings SET status=%s WHERE id=%s', (target, booking_id))
            if target == 'completed':
                cur.execute('UPDATE users SET points=points+%s WHERE id=%s',
                            (int(row['price']) // 100, row['customer_id']))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class App(tk.Tk):
    def __init__(self, auto_connect=True):
        if sys.platform=='win32':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('LumiereClinic.Final.1')
            except (OSError,AttributeError):
                pass
        super().__init__()
        global UI_FONT
        available=set(tkfont.families(self))
        UI_FONT=next((name for name in ('Leelawadee UI','Noto Sans Thai','Tahoma') if name in available),'TkDefaultFont')
        self.title('Lumiére Clinic | ระบบบริหารคลินิกความงาม')
        self.clinic_icon = None
        self.brand_icon = None
        try:
            self.clinic_icon = tk.PhotoImage(file=str(BASE/'assets'/'clinic_logo.png'))
            self.brand_icon = self.clinic_icon.subsample(8,8)
            self.iconphoto(True,self.clinic_icon)
            if sys.platform=='win32':
                self.iconbitmap(str(BASE/'assets'/'clinic_logo.ico'))
        except tk.TclError:
            pass
        self.geometry('1180x780')
        self.minsize(940, 650)
        self.configure(bg=CREAM)
        self.db, self.user = None, None
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=(UI_FONT, 12), background=CREAM, foreground=INK)
        style.configure('TButton', padding=(14,10), borderwidth=0, background='#EEE8DE')
        style.configure('Gold.TButton', background=GOLD, foreground=WHITE)
        style.map('Gold.TButton', background=[('active','#AA8848'),('disabled','#D5C7AD')])
        style.configure('TEntry',padding=7,fieldbackground=WHITE,bordercolor='#E7DFD2')
        style.configure('TCombobox',padding=7,fieldbackground=WHITE,bordercolor='#E7DFD2')
        style.map('TCombobox',fieldbackground=[('readonly',WHITE)],selectbackground=[('readonly',WHITE)],selectforeground=[('readonly',INK)])
        style.configure('TNotebook',borderwidth=0)
        style.configure('TNotebook.Tab',padding=(18,10),background='#F0EAE0')
        style.map('TNotebook.Tab',background=[('selected',WHITE)],foreground=[('selected','#9E7A30')])
        style.configure('Treeview', rowheight=38, background=WHITE, fieldbackground=WHITE)
        style.configure('Treeview.Heading', background='#EFE7D7', font=(UI_FONT, 11, 'bold'))
        style.map('Treeview',background=[('selected','#EAE0CC')],foreground=[('selected',INK)])
        self.report_callback_exception = lambda typ, value, tb: messagebox.showerror('เกิดข้อผิดพลาด', str(value))
        self.connection_results = queue.Queue()
        self.connecting = False
        self.login_screen()
        if auto_connect:
            self.after(80,self.connect_background)

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def scroll_content(self, parent, padding=0):
        shell = ttk.Frame(parent)
        shell.pack(fill='both',expand=True)
        canvas = tk.Canvas(shell,bg=CREAM,highlightthickness=0)
        scrollbar = ttk.Scrollbar(shell,orient='vertical',command=canvas.yview)
        scrollbar.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        body = ttk.Frame(canvas,padding=padding)
        item = canvas.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        top = parent.winfo_toplevel()
        def wheel(event):
            if str(event.widget).startswith(str(shell)) and canvas.winfo_exists():
                canvas.yview_scroll(-int(event.delta/120),'units')
        binding = top.bind('<MouseWheel>',wheel,add='+')
        shell.bind('<Destroy>',lambda e:top.unbind('<MouseWheel>',binding) if e.widget==shell else None)
        return body

    def title_text(self, parent, title, subtitle=''):
        ttk.Label(parent, text=title, font=(UI_FONT, 22, 'normal'), foreground=GOLD).pack(anchor='w', pady=(12, 6))
        if subtitle:
            ttk.Label(parent, text=subtitle, wraplength=850).pack(anchor='w', pady=(0, 16))

    def field(self, parent, label, default='', values=None, secret=False):
        ttk.Label(parent, text=label).pack(anchor='w', pady=(8, 3))
        var = tk.StringVar(value=str(default))
        if secret:
            holder = ttk.Frame(parent)
            holder.pack(fill='x',pady=(0,3))
            widget = ttk.Entry(holder,textvariable=var,show='•')
            widget.pack(side='left',fill='x',expand=True)
            def toggle():
                visible = bool(widget.cget('show'))
                widget.configure(show='' if visible else '•')
                eye.configure(text='◉ ซ่อน' if visible else '◉ แสดง')
            eye = ttk.Button(holder,text='◉ แสดง',width=8,command=toggle,takefocus=True)
            eye.pack(side='right',padx=(6,0))
            holder.password_entry, holder.visibility_button = widget,eye
            return var
        if values is None:
            widget = ttk.Entry(parent, textvariable=var)
        else:
            widget = ttk.Combobox(parent, textvariable=var, values=values, state='readonly')
        widget.pack(fill='x', pady=(0, 3))
        return var

    def button(self, parent, label, command, gold=False):
        button = ttk.Button(parent, text=label, command=safe(command), style='Gold.TButton' if gold else 'TButton')
        button.pack(side='left', padx=(0, 8), pady=10)
        return button

    def modal(self, title, size='620x680'):
        win = tk.Toplevel(self)
        win.title(title)
        if self.clinic_icon:
            win.iconphoto(False,self.clinic_icon)
        if sys.platform=='win32' and (BASE/'assets'/'clinic_logo.ico').exists():
            win.iconbitmap(str(BASE/'assets'/'clinic_logo.ico'))
        win.geometry(size)
        win.configure(bg=CREAM)
        win.transient(self)
        win.grab_set()
        ClinicImage(win,height=64,title='BEAUTY & WELLNESS',caption='Lumiére Clinic').pack(fill='x')
        body = self.scroll_content(win,padding=22)
        return win, body

    def connect_background(self):
        if self.connecting or self.db:
            return
        self.connecting = True
        self.connection_status.set('กำลังเตรียมระบบ กรุณารอสักครู่...')
        def worker():
            try:
                config = json.loads((BASE / 'config.json').read_text(encoding='utf-8'))
                self.connection_results.put((Database(config), None))
            except Exception as exc:
                self.connection_results.put((None, exc))
        threading.Thread(target=worker, daemon=True).start()
        self.after(100,self.poll_connection)

    def poll_connection(self):
        try:
            db, error = self.connection_results.get_nowait()
        except queue.Empty:
            self.after(100,self.poll_connection)
            return
        self.connecting = False
        if error:
            self.connection_status.set('ระบบยังไม่พร้อม กรุณาติดต่อเจ้าหน้าที่ หรือกดลองเชื่อมต่อใหม่')
            self.retry_button.pack(anchor='w',pady=4)
        else:
            self.db = db
            self.connection_status.set('พร้อมให้บริการ • เปิด 09:00–18:00 / หยุดวันพุธ')
            self.retry_button.pack_forget()

    def require_database(self):
        if not self.db:
            raise ValueError('ระบบกำลังเตรียมพร้อม หรือไม่สามารถติดต่อเซิร์ฟเวอร์ได้ กรุณารอสักครู่แล้วลองอีกครั้ง')

    def login_screen(self):
        self.user = None
        self.clear()
        shell = ttk.Frame(self,padding=24)
        shell.pack(fill='both',expand=True)
        visual = ClinicImage(shell,height=620,width=470)
        visual.pack(side='left',fill='both',expand=True,padx=(0,28))
        body = ttk.Frame(shell,padding=(10,12),width=420)
        body.pack(side='right',fill='y')
        if self.brand_icon:
            ttk.Label(body,image=self.brand_icon).pack(anchor='w',pady=(0,8))
        self.title_text(body, 'Lumiére Clinic', 'BEAUTY & WELLNESS CLINIC\nให้การดูแลตัวเอง เริ่มต้นได้อย่างง่ายดาย')
        self.connection_status = tk.StringVar(value='พร้อมให้บริการ • หยุดทุกวันพุธ' if self.db else 'กำลังเตรียมระบบ...')
        ttk.Label(body,textvariable=self.connection_status,wraplength=370,foreground='#8C7754').pack(anchor='w',pady=(0,10))
        self.retry_button = ttk.Button(body,text='ลองเชื่อมต่อใหม่',command=self.connect_background)
        if not self.db and not self.connecting:
            self.retry_button.pack(anchor='w',pady=4)
        username = self.field(body, 'ชื่อผู้ใช้')
        password = self.field(body, 'รหัสผ่าน', secret=True)
        def login():
            self.require_database()
            user = self.db.authenticate(username.get(),password.get())
            # Role is always taken from the authenticated DB account, never from user input.
            self.user = user
            self.home()
        bar = ttk.Frame(body)
        bar.pack(anchor='w')
        self.button(bar, 'เข้าสู่ระบบ', login, True)
        self.button(bar, 'สมัครสมาชิก', self.register)
        bar2 = ttk.Frame(body)
        bar2.pack(anchor='w')
        self.button(bar2, 'ลืมรหัสผ่าน?', self.forgot)
        ttk.Label(body,text='ระบบเปิดหน้าตามสิทธิ์บัญชีให้อัตโนมัติ\nชื่อผู้ใช้ใช้ตัวพิมพ์ใหญ่หรือเล็กได้',foreground='#8C7754').pack(anchor='w',pady=8)
        ttk.Label(body,text='ดูแลอย่างใส่ใจ ในทุกขั้นตอนของความงาม',foreground='#8C7754').pack(anchor='w',pady=18)

    def register(self):
        self.require_database()
        win, body = self.modal('สมัครสมาชิกผู้รับบริการ', '620x760')
        self.title_text(body, 'สร้างบัญชีของคุณ')
        fields = {key: self.field(body,label,secret=key in ('password','confirm','answer')) for key,label in
                  [('username','ชื่อผู้ใช้ (อังกฤษ/ตัวเลข 3–80 ตัว)'),('name','ชื่อ–นามสกุล'),('phone','เบอร์โทรศัพท์'),
                   ('password','รหัสผ่าน อย่างน้อย 8 ตัว'),('confirm','ยืนยันรหัสผ่าน'),
                   ('question','คำถามกันลืม'),('answer','คำตอบกันลืม')]}
        def save():
            data = {k:v.get().strip() if k not in ('password','confirm') else v.get() for k,v in fields.items()}
            if not all(data.values()):
                raise ValueError('กรุณากรอกข้อมูลให้ครบ')
            if not re.fullmatch(r'[A-Za-z0-9_.-]{3,80}', data['username']):
                raise ValueError('ชื่อผู้ใช้ไม่ถูกต้อง')
            if not re.fullmatch(r'\+?[0-9]{9,15}', data['phone']):
                raise ValueError('เบอร์โทรศัพท์ไม่ถูกต้อง')
            strong_password(data['password'])
            if data['password'] != data['confirm']:
                raise ValueError('รหัสผ่านยืนยันไม่ตรงกัน')
            self.db.query('''INSERT INTO users(username,password_hash,role,full_name,phone,security_question,security_answer)
                VALUES(%s,%s,'customer',%s,%s,%s,%s)''', (data['username'],password_hash(data['password']),
                data['name'], data['phone'], data['question'],password_hash(data['answer'].casefold())))
            messagebox.showinfo('สำเร็จ', 'สมัครสมาชิกแล้ว สามารถเข้าสู่ระบบได้')
            win.destroy()
        bar = ttk.Frame(body)
        bar.pack()
        self.button(bar, 'สมัครสมาชิก', save, True)

    def forgot(self):
        self.require_database()
        win, body = self.modal('ลืมรหัสผ่าน', '620x600')
        self.title_text(body, 'กู้คืนบัญชี', 'ยืนยันด้วยคำถามกันลืม สามารถลองตอบได้ 5 ครั้งต่อหน้าต่าง')
        role = self.field(body,'บทบาท','ผู้รับบริการ',list(ROLES))
        username = self.field(body,'ชื่อผู้ใช้')
        question = ttk.Label(body,text='',wraplength=550)
        question.pack(anchor='w',pady=8)
        answer = self.field(body,'คำตอบ',secret=True)
        new = self.field(body,'รหัสผ่านใหม่',secret=True)
        confirm = self.field(body,'ยืนยันรหัสผ่านใหม่',secret=True)
        state = {'account': None, 'attempts': 0}
        def load():
            state['account'] = self.db.query('SELECT * FROM users WHERE username=%s AND role=%s',
                                            (username.get().strip(), ROLES[role.get()]),one=True)
            if not state['account']:
                raise ValueError('ไม่พบบัญชีตามชื่อผู้ใช้และบทบาทนี้')
            question.config(text=state['account']['security_question'])
        def reset():
            account = state['account']
            if not account:
                raise ValueError('กดแสดงคำถามก่อน')
            state['attempts'] += 1
            if state['attempts'] > 5:
                win.destroy()
                raise ValueError('เกินจำนวนครั้ง กรุณาติดต่อผู้ดูแลระบบ')
            if not password_ok(answer.get().strip().casefold(), account['security_answer']):
                raise ValueError('คำตอบไม่ถูกต้อง')
            strong_password(new.get())
            if new.get() != confirm.get():
                raise ValueError('รหัสผ่านยืนยันไม่ตรงกัน')
            self.db.query('UPDATE users SET password_hash=%s WHERE id=%s', (password_hash(new.get()), account['id']))
            messagebox.showinfo('สำเร็จ','เปลี่ยนรหัสผ่านแล้ว')
            win.destroy()
        bar = ttk.Frame(body)
        bar.pack()
        self.button(bar,'แสดงคำถาม',load)
        self.button(bar,'ตั้งรหัสผ่านใหม่',reset,True)

    def home(self):
        self.clear()
        head = ttk.Frame(self,padding=(22,10))
        head.pack(fill='x')
        if self.brand_icon:
            ttk.Label(head,image=self.brand_icon).pack(side='left',padx=(0,12))
        ttk.Label(head,text='Lumiére Clinic',font=(UI_FONT,22,'bold'),foreground=GOLD).pack(side='left')
        ttk.Label(head,text=f"  |  {self.user['full_name']} ({self.user['role']})").pack(side='left')
        ttk.Button(head,text='ออกจากระบบ',command=self.login_screen).pack(side='right')
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both',expand=True,padx=20,pady=(0,20))
        self.dashboard = self.tab('ภาพรวม',scroll=True)
        self.build_dashboard()
        if self.user['role']=='customer':
            self.booking_page = self.tab('จองบริการ',scroll=True)
            self.build_booking(self.booking_page)
        self.build_catalog(self.tab('บริการและหัตถการ',scroll=True))
        self.queue_page = self.tab('ประวัติและคิวของฉัน' if self.user['role']=='customer' else 'ตารางคิวและเคส')
        self.build_queues()
        if self.user['role']=='admin':
            self.build_management(self.tab('แพทย์และหัตถการ'))

    def tab(self, name, scroll=False):
        page = ttk.Frame(self.tabs,padding=18)
        self.tabs.add(page,text=name)
        return self.scroll_content(page) if scroll else page

    def build_dashboard(self):
        for child in self.dashboard.winfo_children():
            child.destroy()
        body = self.dashboard
        ClinicImage(body,height=140,title='YOUR BEAUTY, OUR CARE').pack(fill='x',pady=(0,8))
        self.title_text(body,'ยินดีต้อนรับ',datetime.now().strftime('%d/%m/%Y'))
        role = self.user['role']
        if role=='customer':
            profile = self.db.query('SELECT * FROM users WHERE id=%s',(self.user['id'],),one=True)
            upcoming = self.db.query("SELECT COUNT(*) n FROM bookings WHERE customer_id=%s AND starts_at>=NOW() AND status IN ('pending','approved','confirmed')",(self.user['id'],),one=True)
            metrics=[('REWARD POINTS',f"{profile['points']:,}",'แต้มสะสม'),('UPCOMING VISITS',str(upcoming['n']),'นัดหมายที่กำลังมาถึง'),('MEMBERSHIP','LUMIÉRE','สมาชิกคลินิก')]
            text = f"{profile['full_name']}\nโทรศัพท์: {profile['phone']}\nแต้มสะสม: {profile['points']:,} แต้ม\nสิทธิสมาชิก: รับ 1 แต้มต่อยอดบริการสำเร็จ 100 บาท\nการใช้แต้ม: ติดต่อเจ้าหน้าที่คลินิก"
        elif role=='admin':
            stats = self.db.query('''SELECT SUM(DATE(starts_at)=CURDATE() AND status<>'cancelled') today,
                SUM(status='pending') pending, COALESCE(SUM(CASE WHEN status='completed' THEN price ELSE 0 END),0) revenue
                FROM bookings''',one=True)
            metrics=[('TODAY',str(stats['today'] or 0),'คิววันนี้'),('PENDING',str(stats['pending'] or 0),'คำขอรออนุมัติ'),('REVENUE',f"{stats['revenue']:,.0f}",'รายได้จำลอง / บาท')]
            text = f"คิววันนี้: {stats['today'] or 0}\nคิวรออนุมัติ: {stats['pending'] or 0}\nรายได้จำลองจากบริการสำเร็จ: {stats['revenue']:,.2f} บาท"
        else:
            stats = self.db.query('''SELECT COUNT(*) n FROM bookings b JOIN doctors d ON d.id=b.doctor_id
                WHERE d.user_id=%s AND DATE(b.starts_at)=CURDATE() AND b.status<>'cancelled' ''', (self.user['id'],),one=True)
            alerts = self.db.query('''SELECT n.note,n.booking_id FROM dispatches n
                JOIN bookings b ON b.id=n.booking_id JOIN doctors d ON d.id=b.doctor_id
                WHERE d.user_id=%s ORDER BY n.id DESC LIMIT 3''',(self.user['id'],))
            text = f"ตารางแพทย์ {self.user['full_name']}\nจำนวนคิววันนี้: {stats['n']}\nข้อความประสานงานล่าสุด:"
            text += ''.join(f"\n• คิว #{r['booking_id']}: {r['note'][:100]}" for r in alerts) or '\nยังไม่มีข้อความ'
            metrics=[('TODAY',str(stats['n']),'นัดหมายวันนี้'),('CARE TEAM',str(len(alerts)),'ข้อความประสานงานล่าสุด'),('SCHEDULE','09:00–18:00','หยุดทุกวันพุธ')]
        tiles=ttk.Frame(body)
        tiles.pack(fill='x',pady=(5,12))
        for i,(label,value,caption) in enumerate(metrics):
            tiles.columnconfigure(i,weight=1,uniform='metrics')
            tile=tk.Frame(tiles,bg=WHITE,highlightbackground='#E8DFD1',highlightthickness=1,padx=18,pady=18)
            tile.grid(row=0,column=i,sticky='nsew',padx=(0,12) if i<2 else 0)
            tk.Label(tile,text=label,bg=WHITE,fg='#9D8B70',font=(UI_FONT,9)).pack(anchor='w')
            tk.Label(tile,text=value,bg=WHITE,fg=GOLD,font=('Georgia',23)).pack(anchor='w',pady=7)
            tk.Label(tile,text=caption,bg=WHITE,fg=INK,font=(UI_FONT,11)).pack(anchor='w')
        card = tk.Label(body,text=text,bg=WHITE,fg=INK,font=(UI_FONT,16),justify='left',anchor='nw',padx=28,pady=28,wraplength=850)
        card.pack(fill='x',pady=16)
        bar = ttk.Frame(body)
        bar.pack(anchor='w')
        self.button(bar,'รีเฟรชภาพรวม',self.build_dashboard)

    def build_booking(self, body):
        ClinicImage(body,height=115,title='MAKE TIME FOR YOURSELF',caption='Lumiére Clinic  /  RESERVATION').pack(fill='x',pady=(0,8))
        self.title_text(body,'จองเวลาสำหรับคุณ','เปิด 09:00–18:00 • คลินิกหยุดทุกวันพุธ')
        doctors = self.db.query('''SELECT d.*,u.full_name FROM doctors d JOIN users u ON u.id=d.user_id WHERE d.active=1 ORDER BY d.id''')
        treatments = self.db.query('SELECT * FROM treatments WHERE active=1 ORDER BY id')
        dmap = {f"{x['id']} • {x['full_name']} | {x['specialty']}":x for x in doctors}
        tmap = {f"{x['id']} • {x['name']} | {x['price']:,.0f} บาท / {x['duration']} นาที":x for x in treatments}
        split = ttk.Frame(body)
        split.pack(fill='both',expand=True,pady=8)
        preview = tk.Frame(split,bg=WHITE,highlightbackground='#E8DFD1',highlightthickness=1,width=300)
        preview.pack(side='right',fill='y',padx=(20,0))
        photo = ClinicImage(preview,height=230,width=300,overlay=False)
        photo.pack(fill='x')
        tk.Label(preview,text='YOUR PERSONAL TREATMENT',bg=WHITE,fg=GOLD,font=(UI_FONT,9)).pack(anchor='w',padx=16,pady=(18,8))
        preview_title = tk.Label(preview,bg=WHITE,fg=INK,font=(UI_FONT,16,'normal'),wraplength=270,justify='left')
        preview_title.pack(anchor='w',padx=16)
        preview_detail = tk.Label(preview,bg=WHITE,fg='#6D655B',font=(UI_FONT,11),wraplength=270,justify='left')
        preview_detail.pack(anchor='w',padx=16,pady=14)
        preview_price = tk.Label(preview,bg='#F5F0E6',fg='#977638',font=(UI_FONT,14,'bold'),padx=12,pady=12)
        preview_price.pack(fill='x',padx=16,pady=12)
        tk.Label(preview,text='ภาพจำลองประกอบบริการ\nแพทย์ประเมินความเหมาะสมก่อนรับบริการ',bg=WHITE,fg='#8E8374',font=(UI_FONT,9),wraplength=260,justify='left').pack(anchor='w',padx=16,pady=12)
        body = ttk.Frame(split)
        body.pack(side='left',fill='both',expand=True)
        doctor = self.field(body,'เลือกแพทย์', next(iter(dmap),''),list(dmap))
        treatment = self.field(body,'เลือกหัตถการ', next(iter(tmap),''),list(tmap))
        self.booking_treatment, self.booking_treatment_map = treatment,tmap
        def refresh_preview(*args):
            row = tmap.get(treatment.get())
            if row:
                photo.set_asset(treatment_asset(row['name']))
                preview_title.configure(text=row['name'])
                preview_detail.configure(text=row['description'])
                preview_price.configure(text=f"เริ่มต้น {row['price']:,.0f} บาท\nประมาณ {row['duration']} นาที")
        treatment.trace_add('write',refresh_preview)
        refresh_preview()
        day = tk.StringVar(value=str(next_booking_day(date.today())))
        ttk.Label(body,text='วันที่นัดหมาย').pack(anchor='w',pady=(8,3))
        date_bar = ttk.Frame(body)
        date_bar.pack(fill='x')
        date_display = tk.StringVar()
        def show_date():
            value = date.fromisoformat(day.get())
            date_display.set(f'{value.day} {BookingCalendar.MONTHS[value.month-1]} {value.year+543}')
        show_date()
        ttk.Entry(date_bar,textvariable=date_display,state='readonly',width=28).pack(side='left',fill='x',expand=True)
        def selected_date(value):
            day.set(str(value))
            show_date()
            refresh_times()
        def open_calendar():
            self.booking_calendar = BookingCalendar(self,date.fromisoformat(day.get()),selected_date)
        ttk.Button(date_bar,text='เลือกจากปฏิทิน',command=open_calendar,style='Gold.TButton').pack(side='left',padx=(10,0))
        times = [f'{h:02}:{m:02}' for h in range(9,18) for m in (0,30)]
        time = self.field(body,'เวลาเริ่ม','09:00',times)
        time_widget = body.winfo_children()[-1]
        def refresh_times(*args):
            value = tmap.get(treatment.get())
            duration = value['duration'] if value else 30
            selected_day = date.fromisoformat(day.get())
            available = []
            for slot in times:
                start = datetime.strptime(day.get()+' '+slot,'%Y-%m-%d %H:%M')
                if (booking_day_allowed(selected_day) and start>datetime.now()
                        and start+timedelta(minutes=duration)<=start.replace(hour=18,minute=0)):
                    available.append(slot)
            time_widget.configure(values=available)
            if time.get() not in available:
                time.set(available[0] if available else '')
        treatment.trace_add('write',refresh_times)
        refresh_times()
        ttk.Label(body,text='เลือกได้ตั้งแต่วันนี้ ยกเว้นวันพุธ\nเวลาที่ผ่านไปแล้วจะไม่แสดง',foreground='#8C7754',wraplength=400).pack(anchor='w',pady=(6,0))
        def guide():
            row = tmap.get(treatment.get())
            if not row:
                raise ValueError('กรุณาเลือกหัตถการ')
            self.show_treatment_guide(row)
        def reserve():
            if doctor.get() not in dmap or treatment.get() not in tmap:
                raise ValueError('กรุณาเลือกแพทย์และหัตถการ')
            if not time.get():
                raise ValueError('วันนี้ไม่มีเวลาเปิดรับจองเหลือแล้ว กรุณาเลือกวันอื่น')
            start = datetime.strptime(day.get()+' '+time.get(),'%Y-%m-%d %H:%M')
            if messagebox.askyesno('ยืนยันการจอง', f"{treatment.get()}\n{doctor.get()}\n{start:%d/%m/%Y %H:%M}\nยืนยันส่งคำขอจองหรือไม่?"):
                self.db.book(self.user['id'],dmap[doctor.get()]['id'],tmap[treatment.get()]['id'],start)
                messagebox.showinfo('สำเร็จ','จองคิวแล้ว รอผู้ดูแลอนุมัติ')
                self.refresh_queues()
        bar = ttk.Frame(body)
        bar.pack(anchor='w')
        self.button(bar,'คำอธิบายหัตถการ & ความรู้',guide)
        self.button(bar,'ยืนยันจองคิว',reserve,True)

    def show_treatment_guide(self,row):
        win,content = self.modal('รู้จักหัตถการ • '+row['name'],'850x760')
        ClinicImage(content,height=280,asset=treatment_asset(row['name']),overlay=False).pack(fill='x')
        self.title_text(content,row['name'],f"ราคาเริ่มต้นประมาณ {row['price']:,.0f} บาท  •  ระยะเวลา {row['duration']} นาที")
        for heading,key in [('เกี่ยวกับบริการ','description'),('ข้อดีที่อาจได้รับ','benefits'),('การพักฟื้นและข้อควรทราบ','recovery')]:
            card = tk.Frame(content,bg=WHITE,padx=18,pady=14)
            card.pack(fill='x',pady=6)
            tk.Label(card,text=heading,bg=WHITE,fg=GOLD,font=(UI_FONT,12,'bold')).pack(anchor='w')
            label = tk.Label(card,text=row[key],bg=WHITE,fg=INK,font=(UI_FONT,11),justify='left',wraplength=650)
            label.pack(anchor='w',pady=(8,0),fill='x')
            label.bind('<Configure>',lambda e,w=label:w.configure(wraplength=max(120,e.width-10)))
        ttk.Label(content,text='ภาพจำลองเพื่ออธิบายลักษณะบริการ • ราคาและรายละเอียดเป็นตัวอย่างสำหรับนำเสนอ\nผลลัพธ์และความเหมาะสมต้องได้รับการประเมินโดยแพทย์',foreground='#8C7754',wraplength=680).pack(anchor='w',pady=14)
        bar=ttk.Frame(content)
        bar.pack(anchor='w')
        self.button(bar,'ปิดรายละเอียด',win.destroy)

    def build_catalog(self,body):
        ClinicImage(body,height=130,title='THE ART OF PERSONAL CARE',caption="Lumiére Clinic  /  OUR TREATMENTS").pack(fill='x')
        self.title_text(body,'การดูแลที่ออกแบบเพื่อคุณ','สำรวจบริการ ดูภาพประกอบ และอ่านข้อมูลก่อนตัดสินใจ')
        grid=ttk.Frame(body)
        grid.pack(fill='x',pady=8)
        rows=self.db.query('SELECT * FROM treatments WHERE active=1 ORDER BY id')
        cards=[]
        for row in rows:
            card=tk.Frame(grid,bg=WHITE,highlightbackground='#E8DFD1',highlightthickness=1)
            cards.append(card)
            ClinicImage(card,height=220,width=280,asset=treatment_asset(row['name']),overlay=False,natural_ratio=True).pack(fill='x')
            inner=tk.Frame(card,bg=WHITE,padx=18,pady=16)
            inner.pack(fill='both',expand=True)
            tk.Label(inner,text=row['name'],bg=WHITE,fg=INK,font=(UI_FONT,16,'normal'),wraplength=330,anchor='w',justify='left').pack(anchor='w')
            tk.Label(inner,text=f"เริ่มต้น {row['price']:,.0f} บาท  |  {row['duration']} นาที",bg=WHITE,fg=GOLD,font=(UI_FONT,11,'bold')).pack(anchor='w',pady=10)
            label=tk.Label(inner,text=row['description'],bg=WHITE,fg='#6D655B',font=(UI_FONT,10),wraplength=330,justify='left',anchor='nw',height=3)
            label.pack(fill='x')
            label.bind('<Configure>',lambda e,w=label:w.configure(wraplength=max(120,e.width-10)))
            ttk.Button(inner,text='ดูภาพและรายละเอียด',command=safe(lambda r=row:self.show_treatment_guide(r)),style='Gold.TButton').pack(anchor='w',pady=(12,0))
            if self.user and self.user['role']=='customer':
                ttk.Button(inner,text='จองบริการนี้  →',command=safe(lambda r=row:self.select_service(r))).pack(anchor='w',pady=(8,0))
        layout={'columns':None}
        def arrange(event):
            columns=3 if event.width>=1120 else 2 if event.width>=650 else 1
            if columns==layout['columns']:
                return
            layout['columns']=columns
            for c in range(3):
                grid.columnconfigure(c,weight=1 if c<columns else 0,uniform='services' if c<columns else '')
            for i,card in enumerate(cards):
                card.grid(row=i//columns,column=i%columns,sticky='nsew',padx=7,pady=9)
        grid.bind('<Configure>',arrange)
        arrange(type('Size',(),{'width':max(body.winfo_width(),800)})())
        ttk.Label(body,text='ภาพทั้งหมดเป็นภาพจำลองประกอบบริการ ไม่ใช่ภาพคนไข้จริงหรือการรับรองผลลัพธ์',foreground='#8C7754').pack(anchor='w',pady=12)

    def select_service(self,row):
        choice=next((key for key,value in self.booking_treatment_map.items() if value['id']==row['id']),None)
        if not choice:
            raise ValueError('รายการบริการมีการเปลี่ยนแปลง กรุณาเข้าสู่ระบบใหม่')
        self.booking_treatment.set(choice)
        page=self.booking_page
        while page.master!=self.tabs:
            page=page.master
        self.tabs.select(page)

    def build_queues(self):
        body = self.queue_page
        ClinicImage(body,height=95,title='EVERY VISIT MATTERS',caption='Lumiére Clinic  /  APPOINTMENTS').pack(fill='x',pady=(0,12))
        filters = ttk.Frame(body)
        filters.pack(fill='x')
        self.search = tk.StringVar()
        self.filter_date = tk.StringVar()
        self.filter_status = tk.StringVar(value='ทั้งหมด')
        self.filter_period = tk.StringVar(value='ทั้งหมด')
        for label,var,width in [('ค้นหาชื่อ/หัตถการ',self.search,22),('วันที่ YYYY-MM-DD',self.filter_date,14)]:
            ttk.Label(filters,text=label).pack(side='left',padx=4)
            ttk.Entry(filters,textvariable=var,width=width).pack(side='left')
        ttk.Combobox(filters,textvariable=self.filter_status,values=['ทั้งหมด']+list(STATUS.values()),state='readonly',width=16).pack(side='left',padx=6)
        self.button(filters,'ค้นหา',self.refresh_queues,True)
        line = ttk.Frame(body)
        line.pack(fill='x')
        ttk.Label(line,text='ช่วงเวลา').pack(side='left')
        ttk.Combobox(line,textvariable=self.filter_period,values=['ทั้งหมด','วันนี้','7 วันข้างหน้า'],state='readonly',width=18).pack(side='left',padx=6)
        self.filter_doctor = tk.StringVar(value='ทั้งหมด')
        self.doctor_filters = {'ทั้งหมด': None}
        if self.user['role']=='admin':
            rows = self.db.query('SELECT d.id,u.full_name FROM doctors d JOIN users u ON d.user_id=u.id')
            self.doctor_filters.update({f"{r['id']} • {r['full_name']}":r['id'] for r in rows})
            ttk.Combobox(line,textvariable=self.filter_doctor,values=list(self.doctor_filters),state='readonly',width=26).pack(side='left')
        self.button(line,'รีเฟรช',self.refresh_queues)
        holder = ttk.Frame(body)
        holder.pack(fill='both',expand=True,pady=8)
        columns = ('id','date','time','customer','doctor','treatment','price','status')
        self.tree = ttk.Treeview(holder,columns=columns,show='headings',selectmode='browse',height=5)
        for status,color in [('pending','#9C782E'),('approved','#496A59'),('confirmed','#496A59'),
                             ('in_progress','#526C9A'),('completed','#348064'),('cancelled','#A3A09B')]:
            self.tree.tag_configure(status,foreground=color)
        labels = ['คิว','วันที่','เวลา','ผู้รับบริการ','แพทย์','หัตถการ','บาท','สถานะ']
        for col,label,width in zip(columns,labels,[50,100,110,150,150,180,85,130]):
            self.tree.heading(col,text=label)
            self.tree.column(col,width=width,minwidth=50)
        y = ttk.Scrollbar(holder,orient='vertical',command=self.tree.yview)
        x = ttk.Scrollbar(holder,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        holder.rowconfigure(0,weight=1)
        holder.columnconfigure(0,weight=1)
        self.tree.grid(row=0,column=0,sticky='nsew')
        y.grid(row=0,column=1,sticky='ns')
        x.grid(row=1,column=0,sticky='ew')
        actions = ttk.Frame(body)
        # Reserve action space before allocating remaining height to the table.
        actions.pack(fill='x',before=holder)
        self.queue_actions=actions
        role = self.user['role']
        if role=='customer':
            self.button(actions,'ยกเลิกคิวที่เลือก',lambda:self.change('cancelled'))
            self.button(actions,'รายละเอียด/คำแนะนำหลังทำ',self.case_detail)
        elif role=='admin':
            for label,status in [('อนุมัติคิว','approved'),('ยืนยันการนัด','confirmed'),('ยกเลิก','cancelled')]:
                self.button(actions,label,lambda s=status:self.change(s))
            self.button(actions,'แจ้งเตือน/ติดต่อแพทย์',self.dispatch)
        else:
            self.button(actions,'อนุมัติคิวที่เลือก',lambda:self.change('approved'),True)
            self.button(actions,'ยืนยันการนัด',lambda:self.change('confirmed'))
            self.button(actions,'เปิดเคส / บันทึกการรักษา',self.case_detail,True)
            ttk.Label(body,text='เลือกแถวคิว → อนุมัติคิว → ยืนยันการนัด → เปิดเคสเพื่อเริ่มและเสร็จสิ้นบริการ',foreground='#8C7754',wraplength=850).pack(anchor='w',pady=3,before=holder)
        self.refresh_queues()

    def selected(self):
        selection = self.tree.selection()
        if not selection:
            raise ValueError('กรุณาเลือกคิวจากตารางก่อน')
        return self.queue_rows[int(selection[0])]

    def refresh_queues(self):
        previous_selection=self.tree.selection()
        where, params = ['1=1'], []
        role = self.user['role']
        if role=='customer':
            where.append('b.customer_id=%s'); params.append(self.user['id'])
        elif role=='doctor':
            where.append('d.user_id=%s'); params.append(self.user['id'])
        if self.search.get().strip():
            where.append('(u.full_name LIKE %s OR b.treatment_name LIKE %s)')
            params += ['%'+self.search.get().strip()+'%']*2
        if self.filter_date.get().strip():
            value = datetime.strptime(self.filter_date.get().strip(),'%Y-%m-%d').date()
            where.append('DATE(b.starts_at)=%s'); params.append(value)
        if self.filter_status.get()!='ทั้งหมด':
            where.append('b.status=%s'); params.append(next(k for k,v in STATUS.items() if v==self.filter_status.get()))
        if self.filter_period.get()=='วันนี้':
            where.append('DATE(b.starts_at)=CURDATE()')
        elif self.filter_period.get()=='7 วันข้างหน้า':
            where.append('b.starts_at>=CURDATE() AND b.starts_at<DATE_ADD(CURDATE(), INTERVAL 7 DAY)')
        doctor = self.doctor_filters.get(self.filter_doctor.get())
        if doctor:
            where.append('b.doctor_id=%s'); params.append(doctor)
        rows = self.db.query('''SELECT b.*,u.full_name customer,u.phone,du.full_name doctor FROM bookings b
            JOIN users u ON u.id=b.customer_id JOIN doctors d ON d.id=b.doctor_id
            JOIN users du ON du.id=d.user_id WHERE '''+' AND '.join(where)+' ORDER BY b.starts_at DESC,b.id DESC',tuple(params))
        self.queue_rows = {r['id']:r for r in rows}
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert('', 'end',iid=str(r['id']),tags=(r['status'],),values=(r['id'],r['starts_at'].strftime('%Y-%m-%d'),
                f"{r['starts_at']:%H:%M}–{r['ends_at']:%H:%M}",r['customer'],r['doctor'],r['treatment_name'],
                f"{r['price']:,.0f}",STATUS[r['status']]))
        if previous_selection and self.tree.exists(previous_selection[0]):
            self.tree.selection_set(previous_selection[0])
            self.tree.focus(previous_selection[0])
        self.build_dashboard()

    def change(self, status):
        row = self.selected()
        if messagebox.askyesno('ยืนยัน',f"เปลี่ยนคิว #{row['id']} เป็น {STATUS[status]}?"):
            self.db.transition(self.user,row['id'],status)
            self.refresh_queues()

    def dispatch(self):
        row = self.selected()
        note = simpledialog.askstring('ติดต่อแพทย์',f"ข้อความถึง {row['doctor']} สำหรับคิว #{row['id']}",parent=self)
        if note and note.strip():
            self.db.query('INSERT INTO dispatches(booking_id,admin_id,note) VALUES(%s,%s,%s)',
                          (row['id'],self.user['id'],note.strip()))
            messagebox.showinfo('สำเร็จ','บันทึกข้อความแล้ว แพทย์จะเห็นเมื่อเปิดเคสหรือรีเฟรช\nระบบนี้ไม่ได้ส่ง SMS/LINE ภายนอก')

    def case_detail(self):
        row = self.selected()
        win, body = self.modal(f"เคส #{row['id']}",'820x720')
        self.title_text(body,f"{row['customer']} • {row['treatment_name']}",f"{row['starts_at']:%d/%m/%Y %H:%M} | {STATUS[row['status']]} | โทร {row['phone']}")
        tabs = ttk.Notebook(body)
        tabs.pack(fill='both',expand=True)
        record, history = ttk.Frame(tabs,padding=12), ttk.Frame(tabs,padding=12)
        tabs.add(record,text='บันทึกเคส')
        tabs.add(history,text='ประวัติการบริการ')
        ttk.Label(record,text='บันทึกการรักษา').pack(anchor='w')
        notes = tk.Text(record,height=6,wrap='word',font=(UI_FONT,11))
        notes.pack(fill='both',expand=True,pady=6)
        notes.insert('1.0',row['doctor_notes'] or '')
        ttk.Label(record,text='คำแนะนำหลังทำ').pack(anchor='w')
        care = tk.Text(record,height=5,wrap='word',font=(UI_FONT,11))
        care.pack(fill='both',expand=True,pady=6)
        care.insert('1.0',row['post_care'] or '')
        if self.user['role']=='doctor':
            # Only completed service history; doctor must have a case with this customer.
            previous = self.db.query('''SELECT starts_at,treatment_name,doctor_notes,post_care FROM bookings
                WHERE customer_id=%s AND status='completed' ORDER BY starts_at DESC''',(row['customer_id'],))
            dispatches = self.db.query('SELECT note,created_at FROM dispatches WHERE booking_id=%s ORDER BY id DESC',(row['id'],))
        else:
            previous = self.db.query('''SELECT starts_at,treatment_name,doctor_notes,post_care FROM bookings
                WHERE customer_id=%s AND status='completed' ORDER BY starts_at DESC''',(self.user['id'],))
            dispatches = []
            notes.config(state='disabled'); care.config(state='disabled')
        hist = tk.Text(history,wrap='word',font=(UI_FONT,11))
        hist.pack(fill='both',expand=True)
        for r in previous:
            hist.insert('end',f"{r['starts_at']:%d/%m/%Y} — {r['treatment_name']}\nบันทึก: {r['doctor_notes'] or '-'}\nหลังทำ: {r['post_care'] or '-'}\n\n")
        for r in dispatches:
            hist.insert('end',f"ข้อความประสานงาน {r['created_at']}\n{r['note']}\n\n")
        hist.config(state='disabled')
        if self.user['role']=='doctor':
            bar = ttk.Frame(body)
            bar.pack(fill='x')
            def update(status=None):
                n,c = notes.get('1.0','end-1c'),care.get('1.0','end-1c')
                if status:
                    self.db.transition(self.user,row['id'],status,n,c)
                else:
                    count = self.db.query('''UPDATE bookings b JOIN doctors d ON b.doctor_id=d.id
                        SET b.doctor_notes=%s,b.post_care=%s WHERE b.id=%s AND d.user_id=%s
                        AND b.status IN ('approved','confirmed','in_progress','completed')''',
                        (n,c,row['id'],self.user['id']))
                    fresh = self.db.query('SELECT status FROM bookings WHERE id=%s',(row['id'],),one=True)
                    if fresh['status'] not in ('approved','confirmed','in_progress','completed'):
                        raise ValueError('สถานะนี้ยังบันทึกการรักษาไม่ได้')
                self.refresh_queues()
                win.destroy()
            self.button(bar,'บันทึก',update)
            if row['status']=='pending':
                self.button(bar,'อนุมัติคิว',lambda:update('approved'),True)
            self.button(bar,'เริ่มทำหัตถการ',lambda:update('in_progress'))
            self.button(bar,'เสร็จสิ้นหัตถการ',lambda:update('completed'),True)

    def build_management(self, body):
        ClinicImage(body,height=95,title='EXCELLENCE IN EVERY DETAIL',caption='Lumiére Clinic  /  CLINIC MANAGEMENT').pack(fill='x',pady=(0,8))
        self.title_text(body,'จัดการแพทย์และหัตถการ','การลบเป็นการปิดใช้งาน เพื่อรักษาประวัติการจองเดิม')
        self.manage_kind = tk.StringVar(value='แพทย์')
        box = ttk.Combobox(body,textvariable=self.manage_kind,values=['แพทย์','หัตถการ'],state='readonly')
        box.pack(anchor='w')
        box.bind('<<ComboboxSelected>>',lambda e:safe(self.refresh_management)())
        self.manage_tree = ttk.Treeview(body,columns=('id','name','detail','active'),show='headings',selectmode='browse')
        for col,label in [('id','รหัส'),('name','ชื่อ'),('detail','รายละเอียด'),('active','สถานะ')]:
            self.manage_tree.heading(col,text=label)
        self.manage_tree.column('id',width=60)
        self.manage_tree.column('detail',width=350)
        self.manage_tree.pack(fill='both',expand=True,pady=12)
        bar = ttk.Frame(body)
        bar.pack(anchor='w',before=self.manage_tree)
        self.button(bar,'เพิ่ม',lambda:self.edit_master(False),True)
        self.button(bar,'แก้ไข',lambda:self.edit_master(True))
        self.button(bar,'ลบ / ปิดใช้งาน',self.disable_master)
        self.button(bar,'รีเฟรช',self.refresh_management)
        self.refresh_management()

    def refresh_management(self):
        if self.manage_kind.get()=='แพทย์':
            rows = self.db.query('''SELECT d.*,u.username,u.full_name,u.phone FROM doctors d JOIN users u ON u.id=d.user_id ORDER BY d.id''')
        else:
            rows = self.db.query('SELECT * FROM treatments ORDER BY id')
        self.master_rows = {r['id']:r for r in rows}
        self.manage_tree.delete(*self.manage_tree.get_children())
        for r in rows:
            self.manage_tree.insert('','end',iid=str(r['id']),values=(r['id'],r.get('full_name',r.get('name')),
                r.get('specialty',f"{r.get('price',0):,.0f} บาท / {r.get('duration',0)} นาที"),'เปิดใช้งาน' if r['active'] else 'ปิดใช้งาน'))

    def master_selected(self):
        ids = self.manage_tree.selection()
        if not ids:
            raise ValueError('กรุณาเลือกรายการ')
        return self.master_rows[int(ids[0])]

    def disable_master(self):
        row = self.master_selected()
        table = 'doctors' if self.manage_kind.get()=='แพทย์' else 'treatments'
        if messagebox.askyesno('ปิดใช้งาน','ปิดรับจองรายการนี้? คิวเดิมยังคงอยู่และต้องจัดการแยกต่างหาก'):
            self.db.query(f'UPDATE {table} SET active=0 WHERE id=%s',(row['id'],))
            self.refresh_management()

    def edit_master(self, editing):
        row = self.master_selected() if editing else {}
        doctor = self.manage_kind.get()=='แพทย์'
        win, body = self.modal('แก้ไขข้อมูล' if editing else 'เพิ่มข้อมูล','650x750')
        fields = {}
        if doctor:
            spec = [('full_name','ชื่อ–นามสกุล'),('specialty','ความเชี่ยวชาญ'),('phone','โทรศัพท์')]
            if not editing:
                spec += [('username','ชื่อผู้ใช้แพทย์'),('password','รหัสผ่าน (อย่างน้อย 8 ตัว)'),('question','คำถามกันลืม'),('answer','คำตอบกันลืม')]
        else:
            spec = [('name','ชื่อหัตถการ'),('description','คำอธิบาย'),('benefits','ข้อดี'),('recovery','การพักฟื้น/ความเสี่ยง'),('price','ราคา (บาท)'),('duration','ระยะเวลา (นาที สูงสุด 540)')]
        for key,label in spec:
            fields[key] = self.field(body,label,row.get(key,''),secret=key in ('password','answer'))
        active = tk.BooleanVar(value=bool(row.get('active',True)))
        ttk.Checkbutton(body,text='เปิดใช้งาน',variable=active).pack(anchor='w',pady=8)
        def save():
            v = {k:x.get().strip() if k!='password' else x.get() for k,x in fields.items()}
            if not all(v.values()):
                raise ValueError('กรุณากรอกข้อมูลให้ครบ')
            if doctor:
                if not re.fullmatch(r'\+?[0-9]{9,15}',v['phone']):
                    raise ValueError('เบอร์โทรศัพท์ไม่ถูกต้อง')
                if not editing:
                    strong_password(v['password'])
                    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,80}',v['username']):
                        raise ValueError('ชื่อผู้ใช้ต้องเป็นอังกฤษ/ตัวเลข 3–80 ตัว')
                conn = self.db.connect()
                try:
                    cur = conn.cursor()
                    if editing:
                        cur.execute('UPDATE users SET full_name=%s,phone=%s WHERE id=%s',(v['full_name'],v['phone'],row['user_id']))
                        cur.execute('UPDATE doctors SET specialty=%s,active=%s WHERE id=%s',(v['specialty'],active.get(),row['id']))
                    else:
                        cur.execute('''INSERT INTO users(username,password_hash,role,full_name,phone,security_question,security_answer)
                            VALUES(%s,%s,'doctor',%s,%s,%s,%s)''',(v['username'],password_hash(v['password']),v['full_name'],v['phone'],v['question'],password_hash(v['answer'].casefold())))
                        cur.execute('INSERT INTO doctors(user_id,specialty,active) VALUES(%s,%s,%s)',(cur.lastrowid,v['specialty'],active.get()))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
            else:
                from decimal import Decimal, InvalidOperation
                try:
                    price, duration = Decimal(v['price']), int(v['duration'])
                    if not price.is_finite() or price<0 or price>9999999999 or not 1<=duration<=540:
                        raise ValueError()
                except (InvalidOperation,ValueError):
                    raise ValueError('ราคาและระยะเวลาไม่ถูกต้อง')
                values = (v['name'],v['description'],v['benefits'],v['recovery'],price,duration,active.get())
                if editing:
                    self.db.query('UPDATE treatments SET name=%s,description=%s,benefits=%s,recovery=%s,price=%s,duration=%s,active=%s WHERE id=%s', values+(row['id'],))
                else:
                    self.db.query('INSERT INTO treatments(name,description,benefits,recovery,price,duration,active) VALUES(%s,%s,%s,%s,%s,%s,%s)',values)
            win.destroy()
            self.home()
        bar = ttk.Frame(body)
        bar.pack(anchor='w')
        self.button(bar,'บันทึกข้อมูล',save,True)


if __name__=='__main__':
    App().mainloop()
