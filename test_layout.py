"""Verify action buttons actually fit in the visible window, not merely exist."""
import json
from main import App,Database,BASE

def run():
    app=App(auto_connect=False)
    app.attributes('-alpha',0.0)
    errors=[]
    app.report_callback_exception=lambda typ,value,tb:errors.append(str(value))
    try:
        app.db=Database(json.loads((BASE/'config.json').read_text(encoding='utf-8')))
        for role in ('doctor','admin','customer'):
            app.user=app.db.query('SELECT * FROM users WHERE role=%s ORDER BY id',(role,),one=True)
            app.home()
            app.tabs.select(app.queue_page)
            for width,height in ((940,650),(1180,780),(1536,864)):
                app.geometry(f'{width}x{height}+0+0')
                app.update()
                left,top=app.winfo_rootx(),app.winfo_rooty()
                right,bottom=left+app.winfo_width(),top+app.winfo_height()
                for button in app.queue_actions.winfo_children():
                    assert button.winfo_ismapped(),(role,button.cget('text'),'not mapped')
                    x,y=button.winfo_rootx(),button.winfo_rooty()
                    assert left<=x and top<=y and x+button.winfo_width()<=right and y+button.winfo_height()<=bottom,(role,button.cget('text'),width,height,'outside viewport')
                assert app.tree.winfo_height()>40
                assert app.queue_actions.winfo_rooty()<app.tree.winfo_rooty()
                print('Visible actions OK:',role,f'{width}x{height}')
        assert not errors,errors
    finally:
        app.destroy()

if __name__=='__main__':
    run()
