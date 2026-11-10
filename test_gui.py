"""Exercise all main screens using a withdrawn Tk window and the clinic database."""
import os
from datetime import date,timedelta
from main import App, Database, BookingCalendar, booking_day_allowed, treatment_asset


def run():
    app = App(auto_connect=False)
    app.withdraw()
    callback_errors=[]
    app.report_callback_exception=lambda typ,value,tb:callback_errors.append(str(value))
    try:
        assert app.clinic_icon is not None
        app.db = Database(dict(host='127.0.0.1',port=3306,user='root',
                              password=os.environ['BEAUTY_TEST_PASSWORD'],database='project_beauty(Final)'))
        for role in ('customer','admin','doctor'):
            app.user = app.db.query('SELECT * FROM users WHERE role=%s ORDER BY id',(role,),one=True)
            app.home()
            app.update_idletasks()
            assert len(app.tabs.tabs()) >= 2
            if role=='customer':
                for row in app.db.query('SELECT * FROM treatments WHERE active=1 ORDER BY id'):
                    from pathlib import Path
                    assert (Path(__file__).parent/'assets'/treatment_asset(row['name'])).is_file()
                    app.select_service(row)
                    assert app.booking_treatment_map[app.booking_treatment.get()]['id']==row['id']
                    app.show_treatment_guide(row)
                    app.update_idletasks()
                    for child in app.winfo_children():
                        if child.winfo_class()=='Toplevel':
                            child.destroy()
            print('Screen OK:',role)
        chosen=[]
        cal=BookingCalendar(app,date.today(),chosen.append)
        app.update_idletasks()
        for day,button in cal.day_buttons.items():
            assert (str(button['state'])=='normal') == booking_day_allowed(day)
        old_month=cal.month
        cal.move(-1)
        assert cal.month==old_month
        cal.move(1)
        for day,button in cal.day_buttons.items():
            assert (str(button['state'])=='normal') == booking_day_allowed(day)
        closed=next(d for d in cal.day_buttons if d.weekday()==2)
        cal.choose(closed)
        assert not chosen
        allowed=next(d for d in cal.day_buttons if booking_day_allowed(d))
        cal.choose(allowed)
        assert chosen==[allowed]
        print('Calendar OK: past dates, Wednesdays, month navigation, selectable date')
        app.login_screen()
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        holders=[w for w in descendants(app) if hasattr(w,'visibility_button')]
        assert not [w for w in descendants(app) if w.winfo_class()=='TCombobox'], 'Login must not show role dropdown'
        assert len(holders)==1
        holder=holders[0]
        holder.password_entry.insert(0,'Demo12345')
        assert holder.password_entry.cget('show')
        holder.visibility_button.invoke()
        assert holder.password_entry.cget('show')==''
        assert holder.password_entry.get()=='Demo12345'
        holder.visibility_button.invoke()
        assert holder.password_entry.cget('show')
        print('Password visibility OK; service cards, selection and all image guides OK')
        for opener in (app.register,app.forgot):
            opener()
            app.update_idletasks()
            for child in app.winfo_children():
                if child.winfo_class()=='Toplevel':
                    child.destroy()
        assert not callback_errors,callback_errors
        print('PASS: all role dashboards, booking, queues, management, registration, recovery screens')
    finally:
        app.destroy()


if __name__=='__main__':
    run()
