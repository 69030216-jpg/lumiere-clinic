"""Integration checks. Creates and drops only its own randomly named test database.
Set BEAUTY_TEST_PASSWORD before running. The normal clinic database is untouched.
"""
import os
import secrets
from datetime import datetime, timedelta
from main import Database, password_hash, password_ok, next_booking_day


def run():
    config = dict(host='127.0.0.1', port=3306, user='root',
                  password=os.environ['BEAUTY_TEST_PASSWORD'],
                  database='beauty_test_' + secrets.token_hex(6))
    db = None
    try:
        db = Database(config)
        assert len(db.query('SELECT * FROM doctors')) == 3
        assert len(db.query('SELECT * FROM treatments')) == 5
        Database(config)
        assert len(db.query('SELECT * FROM users')) == 5
        customer = db.query("SELECT * FROM users WHERE role='customer'", one=True)
        for spelling in ('Doctor1','doctor1','DOCTOR1',' Doctor1 '):
            assert db.authenticate(spelling,'Demo12345')['role']=='doctor'
        for name,pw in [('Doctor1','wrong'),('missing','Demo12345'),('Doctor1','')]:
            try:
                db.authenticate(name,pw)
                raise AssertionError('Invalid login accepted')
            except ValueError:
                pass
        admin = db.query("SELECT * FROM users WHERE role='admin'", one=True)
        doctors = db.query('SELECT * FROM doctors ORDER BY id')
        doctor = db.query('SELECT * FROM users WHERE id=%s',(doctors[0]['user_id'],),one=True)
        other = db.query('SELECT * FROM users WHERE id=%s',(doctors[1]['user_id'],),one=True)
        treatment = db.query('SELECT * FROM treatments ORDER BY id',one=True)
        start = datetime.now().replace(hour=9,minute=0,second=0,microsecond=0)+timedelta(days=1)
        start = datetime.combine(next_booking_day(start.date()),start.time())
        wednesday = start
        while wednesday.weekday()!=2:
            wednesday += timedelta(days=1)
        for rejected in (wednesday, datetime.now()-timedelta(days=1)):
            try:
                db.book(customer['id'],doctors[0]['id'],treatment['id'],rejected)
                raise AssertionError('Closed or past date accepted')
            except ValueError:
                pass
        db.book(customer['id'],doctors[0]['id'],treatment['id'],start)
        try:
            db.book(customer['id'],doctors[0]['id'],treatment['id'],start)
            raise AssertionError('Double booking was accepted')
        except ValueError:
            pass
        try:
            db.book(customer['id'],doctors[1]['id'],treatment['id'],start)
            raise AssertionError('Customer overlap was accepted')
        except ValueError:
            pass
        row = db.query('SELECT * FROM bookings',one=True)
        db.transition(admin,row['id'],'approved')
        db.transition(admin,row['id'],'confirmed')
        try:
            db.transition(other,row['id'],'in_progress')
            raise AssertionError('Wrong doctor accepted')
        except ValueError:
            pass
        # Simulate an appointment on today's schedule to exercise completion.
        today = datetime.now().replace(hour=9,minute=0,second=0,microsecond=0)
        db.query('UPDATE bookings SET starts_at=%s,ends_at=%s WHERE id=%s',
                 (today,today+timedelta(minutes=treatment['duration']),row['id']))
        db.transition(doctor,row['id'],'in_progress','test notes','test care')
        db.transition(doctor,row['id'],'completed','test notes','test care')
        points = db.query('SELECT points FROM users WHERE id=%s',(customer['id'],),one=True)['points']
        assert points == int(treatment['price'])//100
        try:
            db.transition(doctor,row['id'],'completed','again')
            raise AssertionError('Duplicate completion accepted')
        except ValueError:
            pass
        assert db.query('SELECT points FROM users WHERE id=%s',(customer['id'],),one=True)['points']==points
        assert password_ok('Demo12345',customer['password_hash'])
        assert not password_ok('wrong',customer['password_hash'])
        assert password_ok('beauty',customer['security_answer'])
        db.query('UPDATE users SET password_hash=%s WHERE id=%s',(password_hash('NewPass123'),customer['id']))
        assert password_ok('NewPass123',db.query('SELECT password_hash FROM users WHERE id=%s',(customer['id'],),one=True)['password_hash'])
        db.book(customer['id'],doctors[0]['id'],treatment['id'],start)
        latest = db.query('SELECT id FROM bookings ORDER BY id DESC',one=True)
        db.transition(customer,latest['id'],'cancelled')
        db.book(customer['id'],doctors[0]['id'],treatment['id'],start)
        new_booking=db.query('SELECT * FROM bookings ORDER BY id DESC',one=True)
        try:
            db.transition(other,new_booking['id'],'approved')
            raise AssertionError('Another doctor approved a case')
        except ValueError:
            pass
        db.query('UPDATE bookings SET doctor_notes=%s WHERE id=%s',('preserve me',new_booking['id']))
        db.transition(doctor,new_booking['id'],'approved')
        assert db.query('SELECT doctor_notes FROM bookings WHERE id=%s',(new_booking['id'],),one=True)['doctor_notes']=='preserve me'
        db.transition(doctor,new_booking['id'],'confirmed')
        today=datetime.now().replace(hour=9,minute=0,second=0,microsecond=0)
        db.query('UPDATE bookings SET starts_at=%s,ends_at=%s WHERE id=%s',
                 (today,today+timedelta(minutes=treatment['duration']),new_booking['id']))
        db.transition(doctor,new_booking['id'],'in_progress','assessment','post care')
        db.transition(doctor,new_booking['id'],'completed','assessment','post care')
        print('PASS: doctor approves own queue, confirms, starts and completes; other doctor denied; notes preserved')
        # This completed appointment is moved to yesterday so overlap checks below remain isolated.
        db.query('UPDATE bookings SET starts_at=%s,ends_at=%s WHERE id=%s',
                 (today-timedelta(days=1),today-timedelta(days=1)+timedelta(minutes=treatment['duration']),new_booking['id']))
        print('PASS: seed/idempotency, password/reset, overlap, role isolation, status workflow, points once, cancellation/rebooking')
    finally:
        if db:
            conn = db.connect(True)
            try:
                conn.cursor().execute('DROP DATABASE `' + config['database'] + '`')
                print('Test database removed')
            finally:
                conn.close()


if __name__=='__main__':
    run()
