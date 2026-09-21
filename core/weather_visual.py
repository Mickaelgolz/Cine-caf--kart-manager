"""Local deterministic weather cards: no network and no external image dependencies."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os


def font(size, bold=False):
    candidates = [Path(os.environ.get('WINDIR','C:/Windows')) / 'Fonts' / ('arialbd.ttf' if bold else 'arial.ttf'),
                  Path('/usr/share/fonts/truetype/dejavu') / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path),size)
    return ImageFont.load_default()


def icon(draw,x,y,code,is_day=True):
    if code < 0:
        draw.text((x,y),"?",font=font(25,True),fill="#8C9BAD",anchor="mm")
        return
    if code in (0,1,2):
        if is_day:
            draw.ellipse((x-12,y-12,x+12,y+12),fill='#F2C500')
            for dx,dy in [(0,-22),(0,22),(-22,0),(22,0),(-16,-16),(16,-16),(-16,16),(16,16)]:
                draw.line((x+dx*.75,y+dy*.75,x+dx,y+dy),fill='#D9AD00',width=3)
        else:
            draw.ellipse((x-15,y-15,x+15,y+15),fill='#52739B')
            draw.ellipse((x-6,y-19,x+18,y+8),fill='#F2F4F7')
    if code not in (0,1):
        for dx,dy,r in [(-10,5,11),(2,-2,14),(16,6,10)]:
            draw.ellipse((x+dx-r,y+dy-r,x+dx+r,y+dy+r),fill='#8C9BAD')
        draw.rounded_rectangle((x-19,y+5,x+24,y+15),radius=4,fill='#8C9BAD')
    if code>=51:
        for dx in (-12,0,12):
            draw.line((x+dx,y+23,x+dx-4,y+31),fill='#247BB3',width=3)
    if code>=95:
        draw.polygon([(x+2,y+12),(x-6,y+25),(x+2,y+25),(x-2,y+36),(x+12,y+20),(x+4,y+20)],fill='#D5A300')


def weather_image(forecast):
    rows=forecast.get('hours',[])[:6]
    width=1200; cell=200; height=180
    im=Image.new('RGB',(width,height),'white'); d=ImageDraw.Draw(im)
    def fmt(value,suffix):
        return '-' if value is None else f'{value:g}{suffix}'
    for i,r in enumerate(rows):
        x=(i%6)*cell; y=(i//6)*210
        d.rounded_rectangle((x+3,3,x+cell-3,177),radius=10,fill='#F2F4F7',outline='#D5D9DE')
        stamp=r.get('time','');label=stamp[11:16]
        d.text((x+cell/2,12),label,font=font(19,True),fill='#20252B',anchor='mt')
        hour=int(label[:2]) if label[:2].isdigit() else 12
        daytime=bool(r.get('is_day')) if r.get('is_day') is not None else 6 <= hour < 18
        icon(d,x+cell/2,62,r.get('weather_code',-1),daytime)
        condition=str(r.get('condition') or 'Indisponível')
        if len(condition)>24: condition=condition[:22]+'…'
        d.text((x+cell/2,92),condition,font=font(13,True),fill='#344454',anchor='mt')
        d.text((x+cell/2,116),f"{fmt(r.get('temperature'),'°C')}  •  chuva {fmt(r.get('precipitation_probability'),'%')}",
               font=font(13),fill='#344454',anchor='mt')
        d.text((x+cell/2,141),f"vento {fmt(r.get('wind_speed'),' km/h')}",
               font=font(12),fill='#5D6C7B',anchor='mt')
    return im
