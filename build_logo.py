"""Build the clinic's code-drawn monogram and multi-resolution Windows icon."""
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'vendor'))
from PIL import Image,ImageDraw,ImageFont

def build():
    size=512
    image=Image.new('RGBA',(size,size),(250,247,240,255))
    draw=ImageDraw.Draw(image)
    gold='#BC974F'
    draw.rounded_rectangle((4,4,508,508),radius=112,fill='#FAF7F0',outline=gold,width=8)
    draw.arc((48,48,464,464),start=304,end=614,fill=gold,width=5)
    path=Path('C:/Windows/Fonts/georgia.ttf')
    font=ImageFont.truetype(str(path),280) if path.exists() else ImageFont.load_default(size=240)
    draw.text((256,265),'L',font=font,fill=gold,anchor='mm',stroke_width=1)
    draw.polygon([(385,60),(395,88),(423,98),(395,108),(385,136),(375,108),(347,98),(375,88)],fill=gold)
    target=BASE/'assets'
    target.mkdir(exist_ok=True)
    image.save(target/'clinic_logo.png')
    image.save(target/'clinic_logo.ico',sizes=[(n,n) for n in (16,24,32,48,64,128,256)])
    print('Clinic logo PNG and ICO ready')

if __name__=='__main__':
    build()
