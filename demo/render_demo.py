from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import subprocess, wave, json
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parent
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
REG='/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
SCENES=[
 ('A daily scoop.\nRight on time.', 'An agent for a little joy\nbetween commitments.', 'Meet ScoopScout. It finds an ice cream outing that fits a gap in your day, from wherever you are in San Francisco.', '01-home.jpg',(0,0,834,800),'PROJECT DEMO'),
 ('Start where\nyou are.', 'Choose a location, a destination,\nand your scoop preference.', 'Choose a starting point and where you need to end up. For this demo, we use Dolores Park and a manually entered sample schedule. Google Calendar is not connected yet.', '02-inputs.jpg',(30,825,390,1430),'SAMPLE SCHEDULE · OCT 13'),
 ('A free window.\nA feasible plan.', '12:30–1:00 PM free\n6 min out + 10 min scoop + 6 min back', 'The agent finds a thirty minute gap, checks published shop hours, and allows time for walking, enjoying a scoop, and a buffer before your next commitment.', '03-plan.jpg',(420,825,810,1390),'REAL APP · LIVE QWEN RESULT'),
 ('Your scoop:\nBi-Rite.', 'Return around 12:52 PM.\nEight minutes before the next event.', 'Bi-Rite fits this gap. The estimated outing takes twenty-two minutes, leaving eight minutes before the next busy interval. Source and walking-route links help you verify the plan.', '03-plan.jpg',(420,1460,810,1770),'SOURCED SHOP · ESTIMATED TRAVEL'),
 ('Decisions you\ncan inspect.', 'Calendar gaps → eligible shops\n→ travel budget → preference ranking', 'The decision summary explains the checks. Schedule and location stay in the local app. The Akamai-hosted Qwen model receives shop facts and preferences, without calendar times or coordinates.', '04-decisions.jpg',(420,1380,810,1840),'TRANSPARENT AGENT WORKFLOW'),
 ('New neighborhood.\nNew scoop.', 'Inner Sunset → Hometown Creamery\nEstimated return: 12:42 PM', 'Change the location to the Inner Sunset, and the recommendation changes to Hometown Creamery. The same calendar gap now has a shorter estimated outing.', '05-sunset.jpg',(420,825,810,1390),'LOCATION-AWARE PLANNING'),
 ('Built to fit\nyour day.', '9 sourced SF shops · 15 passing tests\nGoogle connection awaits OAuth setup', 'The prototype includes Google Calendar authorization and five-minute checks while the page is open. Live calendar access still needs OAuth setup. Walking times and shop hours are estimates and snapshots, so check before leaving.', '02-inputs.jpg',(30,1180,390,1460),'HONEST PROTOTYPE STATUS'),
]

def font(size,bold=False):return ImageFont.truetype(BOLD if bold else REG,size)

def lines(draw,text,x,y,size,color,bold=False,spacing=10):
    for line in text.split('\n'):
        draw.text((x,y),line,font=font(size,bold),fill=color)
        y+=size+spacing
    return y

frames=[];srt=[];elapsed=0
for index,(title,desc,narration,shot,crop,tag) in enumerate(SCENES,1):
    audio=ROOT/f'{index:02}-voice.aiff'
    subprocess.run(['say','-v','Samantha','-r','165','-o',str(audio),narration],check=True)
    wav=ROOT/f'{index:02}-voice.wav'
    subprocess.run([FFMPEG,'-y','-loglevel','error','-i',str(audio),str(wav)],check=True)
    with wave.open(str(wav)) as sound:
        if not sound.getnframes():
            raise RuntimeError("Narration is empty; macOS speech service access is required.")
        duration=sound.getnframes()/sound.getframerate()+1.0
    canvas=Image.new('RGB',(1280,720),'#faf7ef');d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((36,30,72,66),18,fill='#275b40');d.text((44,35),'S',font=font(22,True),fill='#faf7ef')
    d.text((84,34),'ScoopScout',font=font(25,True),fill='#23372d')
    d.text((1030,38),f'PROJECT DEMO  /  {index:02}',font=font(13),fill='#6e786c')
    d.line((36,85,1244,85),fill='#dce1d4',width=2)
    lines(d,tag,40,126,12,'#275b40',True)
    y=lines(d,title,40,175,48,'#23372d',True,spacing=12)
    lines(d,desc,40,y+28,19,'#6e786c',spacing=10)
    d.rounded_rectangle((520,116,1240,618),18,fill='#e9edda')
    img=Image.open(ROOT/shot).convert('RGB').crop(crop)
    img=ImageOps.contain(img,(680,478),Image.Resampling.LANCZOS)
    x=520+(720-img.width)//2;y=128+(478-img.height)//2
    canvas.paste(img,(x,y))
    # Burn in short, readable captions; full narration remains in companion SRT.
    d.rounded_rectangle((36,644,1244,700),12,fill='#23372d')
    caption=['Find a scoop that fits your day.','Demo uses a manual sample schedule; Google is not connected.','Find a gap. Check hours. Budget travel and scoop time.','Bi-Rite: estimated return 12:52 PM, before the 1:00 PM commitment.','Private schedule stays local. Qwen ranks eligible shops.','Inner Sunset: Hometown Creamery becomes the nearby pick.','Google OAuth setup required. Travel estimates are approximate.'][index-1]
    d.text((56,661),caption,font=font(19),fill='#faf7ef')
    image=ROOT/f'{index:02}-scene.png';canvas.save(image)
    segment=ROOT/f'{index:02}-segment.mp4'
    subprocess.run([FFMPEG,'-y','-loglevel','error','-loop','1','-i',str(image),'-i',str(wav),'-t',str(duration),'-vf','fps=24,format=yuv420p','-c:v','libx264','-preset','fast','-crf','20','-c:a','aac','-b:a','128k','-af','apad','-movflags','+faststart',str(segment)],check=True)
    frames.append(segment)
    def timestamp(t):
        ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    srt.append(f'{index}\n{timestamp(elapsed)} --> {timestamp(elapsed+duration)}\n{narration}\n')
    elapsed+=duration
    print(f'Scene {index}/{len(SCENES)}: {duration:.1f}s',flush=True)
concat=ROOT/'segments.txt';concat.write_text(''.join("file '"+p.name+"'\n" for p in frames))
subprocess.run([FFMPEG,'-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(ROOT/'ScoopScout-demo.mp4')],check=True)
(ROOT/'ScoopScout-demo.srt').write_text('\n'.join(srt))
(ROOT/'script.txt').write_text('\n\n'.join(s[2] for s in SCENES))
(ROOT/'metadata.json').write_text(json.dumps({'duration_seconds':elapsed,'resolution':'1280x720','scenes':len(SCENES),'video':'ScoopScout-demo.mp4'},indent=2))
print(f'Complete: {elapsed:.1f}s',flush=True)
