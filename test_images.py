"""Exercise native Tk rendering even if Pillow cannot load in Thonny."""
import tkinter as tk
from main import App,ClinicImage,BASE

def run():
    app=App(auto_connect=False)
    app.attributes('-alpha',0.0)
    try:
        app.clear()
        for name in ('botox','filler','ultraformer','rhinoplasty','breast'):
            canvas=ClinicImage(app,asset=name+'.png',overlay=False,width=465,height=310)
            canvas.pack()
            app.update()
            assert canvas.photo is not None
            # Force the Python-version-independent backend used when Pillow fails.
            canvas.source=None
            canvas.native_source=tk.PhotoImage(file=str(BASE/'assets'/(name+'.png')))
            for width,height in ((465,310),(280,190),(600,250)):
                canvas.configure(width=width,height=height)
                app.update()
                canvas.draw()
                assert canvas.photo.width()<=canvas.winfo_width()+6
                assert canvas.photo.height()<=canvas.winfo_height()+6
                coords=canvas.coords(canvas.find_all()[0])
                assert coords==[canvas.winfo_width()/2,canvas.winfo_height()/2]
            canvas.destroy()
            print('Full image / native Tk fallback OK:',name)
    finally:
        app.destroy()

if __name__=='__main__':
    run()
