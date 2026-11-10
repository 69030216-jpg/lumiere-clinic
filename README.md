# Lumiére Clinic

ระบบบริหารจัดการคิวคลินิกความงามแบบ Desktop ด้วย **Python 3, Tkinter และ MySQL** รองรับผู้รับบริการ ผู้ดูแลระบบ และแพทย์

![Lumiére Clinic](assets/clinic_lounge.png)

## ความสามารถ

- เข้าสู่ระบบโดยตรวจบทบาทจากฐานข้อมูล สมัครสมาชิกผู้รับบริการ และกู้รหัสผ่านด้วยคำถามกันลืม
- แกลเลอรีหัตถการ 5 รายการ พร้อมรายละเอียด ราคา และภาพประกอบ
- จองคิวผ่านปฏิทิน ไม่รับวันย้อนหลังหรือวันพุธ และตรวจเวลาซ้อนของแพทย์/ลูกค้า
- ผู้ดูแลค้นหาและกรองคิว อนุมัติ ยืนยันนัด ยกเลิก และประสานงานกับแพทย์
- แพทย์ดูและอนุมัติคิวของตนเอง บันทึกการรักษา เริ่มและเสร็จสิ้นบริการ
- ประวัติบริการ แต้มสะสม และรายได้จำลองจากคิวที่เสร็จสิ้น
- สร้างฐานข้อมูล ตาราง และข้อมูลตัวอย่างอัตโนมัติเมื่อเริ่มใช้

## ติดตั้งและเปิดด้วย Thonny

1. ดาวน์โหลด repository ผ่าน **Code > Download ZIP** แล้วแตกไฟล์ทั้งโฟลเดอร์ หรือ clone ด้วย Git
2. ติดตั้ง Python/Thonny และ MySQL Server แล้วเปิด MySQL Server ให้ทำงาน
3. ใน Thonny ไปที่ **Tools > Manage packages** ติดตั้ง `mysql-connector-python` และ `Pillow` หรือใช้ interpreter เดียวกันรัน:

   ```console
   python -m pip install -r requirements.txt
   ```

4. คัดลอก `config.example.json` เป็น `config.json` ในโฟลเดอร์เดียวกับ `main.py` แล้วใส่ค่าของเครื่องตนเอง:

   ```json
   {
     "host": "127.0.0.1",
     "port": "3306",
     "user": "root",
     "password": "YOUR_MYSQL_PASSWORD",
     "database": "project_beauty(Final)"
   }
   ```

5. บัญชี MySQL ต้องมีสิทธิ์สร้างฐานข้อมูล/ตาราง และอ่านเขียนข้อมูล
6. เปิด `main.py` ใน Thonny แล้วกด **F5** หรือรัน `python main.py`
7. รอข้อความพร้อมให้บริการ แล้วเข้าสู่ระบบ ระบบเชื่อมต่อฐานข้อมูลเบื้องหลัง

`config.json` เป็นไฟล์เฉพาะเครื่องและถูกตัดออกจาก Git ไม่ต้องอัปโหลดรหัสผ่าน MySQL ไป repository

## บัญชีตัวอย่าง

บัญชีเหล่านี้สร้างในฐานข้อมูลของผู้ติดตั้งเมื่อรันครั้งแรก:

| บทบาท | ชื่อผู้ใช้ | รหัสผ่านเริ่มต้น |
|---|---|---|
| ผู้รับบริการ | `customer` | `Demo12345` |
| ผู้ดูแลระบบ | `admin` | `Demo12345` |
| แพทย์ | `doctor1`, `doctor2`, `doctor3` | `Demo12345` |

คำตอบกันลืมเริ่มต้น `beauty` ชื่อผู้ใช้ไม่จำกัดตัวพิมพ์ใหญ่/เล็ก รหัสผ่านต้องพิมพ์ตรงตามตัวอักษร หากเคยเปลี่ยนรหัสผ่านให้ใช้รหัสล่าสุด

## แพทย์อนุมัติคิว

เปิด **ตารางคิวและเคส** คลิกแถวคิว แล้วกด **อนุมัติคิวที่เลือก** และ **ยืนยันการนัด** เหนือตาราง เปิดเคสเพื่อบันทึกและเริ่มหัตถการในวันนัด จากนั้นกดเสร็จสิ้นบริการ

คลินิกเปิด 09:00–18:00 หยุดทุกวันพุธ วันที่ในฐานข้อมูลใช้ ค.ศ. ปฏิทินแสดงเดือนภาษาไทยและ พ.ศ. ตั้งวันที่/เวลาของเครื่องและ MySQL ให้ตรงกัน

## โครงสร้างไฟล์

```text
main.py                 GUI, authentication, booking and database logic
config.example.json     Configuration template without credentials
requirements.txt        Dependencies
assets/                 Treatment images, clinic logo and image prompts
docs/                   Presentation walkthrough
build_logo.py           Rebuild the clinic logo and Windows icon
test_system.py          MySQL integration tests in an isolated database
test_gui.py             GUI smoke tests
test_layout.py          Action-button viewport regression tests
test_images.py          Image resizing and native Tk fallback tests
```

## ตรวจสอบโค้ด

```console
python -m py_compile main.py
```

ชุดทดสอบที่ใช้ MySQL ต้องตั้งการเชื่อมต่อใน `config.json` ส่วน `test_system.py` และ `test_gui.py` ใช้ตัวแปรแวดล้อม `BEAUTY_TEST_PASSWORD` สำหรับ root บน localhost พอร์ต 3306 ตามค่าทดสอบในโค้ด

`test_system.py` สร้างฐานข้อมูลชื่อสุ่ม `beauty_test_*` และลบเฉพาะฐานข้อมูลทดสอบเมื่อจบ ไม่มีการใช้ประวัติผู้ป่วยจริงในการทดสอบ

## ขอบเขตโครงงาน

รายได้เป็นการสรุปจำลอง ไม่มีการชำระเงินจริง ข้อความประสานงานแสดงภายในแอป ไม่มีการส่ง SMS/LINE ภาพหัตถการเป็นภาพจำลองประกอบบริการที่สร้างด้วย AI ไม่ใช่ภาพผู้ป่วยจริง รายละเอียดหัตถการและราคาเป็นตัวอย่างสำหรับการนำเสนอ

คู่มือเพิ่มเติม: [ลำดับนำเสนอ](docs/คู่มือนำเสนอ.md)
