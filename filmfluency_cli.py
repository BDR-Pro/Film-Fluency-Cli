#!/usr/bin/env python3

import os
import re
import sys
import uuid
import csv
import shutil
import argparse
from datetime import datetime, timedelta

# Safe imports with guidance
try:
    import ffmpeg
except ImportError:
    print("Missing 'ffmpeg-python'. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    import nltk
    nltk.download('punkt', quiet=True)
except ImportError:
    print("Missing 'nltk'. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    import textstat
except ImportError:
    print("Missing 'textstat'. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    print("Missing 'moviepy'. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("Missing 'tqdm'. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich import box
except ImportError:
    print("Missing 'rich'. Run: pip install -r requirements.txt")
    sys.exit(1)

# Check for ffmpeg binary
if shutil.which("ffmpeg") is None:
    print("FFmpeg is not installed. Install it from https://ffmpeg.org/download.html")
    sys.exit(1)

console = Console()

def display_ascii_art():
    art = """[cyan]
  .  . .  .  . .  .  . .  .  . .  .  . .  .  
   .       .       .       .       .       . 
     .  .    .  .    .  .    .  .    .  .    
 .       .       .       .       .       .  .
   .  .    . :8%.. %@S .   .:8X. .:@@. .     
  .    .  .t@ :@@8@8X 8X   @S:8@88@8.@@  . . 
    .     . %S8 X8@@SS@ :.:X8; @@@@:;@XS     
  .   . ..%@;tSt@S8;X8:8t88X;tS;@@;8S;8@.  . 
    .    X:S;8;:8X8;.X;t;8ttSt:88X8.XS;X     
  .    . S;t%@t;SX8;:@St%:t;@X:;8@%.@ttt8    
     .    8;t%8X;;%88@;;:;@:;8@ttt%8@S;tS   .
  .       .;::t8@S@8@;;St .;;t8@XX@8;:S@.    
   88;. . .t% 8@888888.:XXX.%@8888::88X.  .  
   XX8t88;     S88@@XSXSSS%8S%t: :88 . . .  .
 . X88@@@8%%X  88888888@@@@XXSXS%@8.     ..  
   @X8@8.%S8X88X@88@@888888@@@@SS8:88@SS%X@  
   8SXX8%@@8;X;Xt8XXXSXXXX88888@@8.S888@888 .
 . 8;X;8@@@X:;tt%S@t@t@t@t@SX@@888.;X8888;8  
   8;%%@X   :;t%%88888888888888XXt;t@888t;8. 
  .8;t%X    .;;;;8XS%@St@tXXSXX:tS;t8@X@t;8. 
   8;ttS .%8.:;:;X;%StSt%S;tttX:;t::;;;;t:8  
 . 8;tt;X8;X@::..tt%tt;tt;t%%tt;;:.@8@8@@X.  
  .8:tX@t%....t .;;;::;:;:;;::::.:8. .       
  .88;:;%S@8@%XS   tXSXXS%Xt  888;8@St;::... 
      . . ....::.:t%tttttS%t:.::.:.. . .     
    .    .  .      .                      .  
[/cyan]"""
    console.print(Panel(art, title="FilmFluency CLI", subtitle="Clip extraction made easy", style="bold cyan", box=box.DOUBLE))

def parse_args():
    parser = argparse.ArgumentParser(description="Extract important dialogue clips from a movie.")
    parser.add_argument('--movie', required=True, help='Path to the movie file')
    parser.add_argument('--srt', required=True, help='Path to the SRT subtitle file')
    parser.add_argument('--screenshot', action='store_true', help='Generate screenshot for each clip')
    parser.add_argument('--s3', help='S3 upload path (requires --id)')
    parser.add_argument('--id', help='Movie ID for S3 (optional unless --s3 is used)')
    args = parser.parse_args()

    if args.s3 and not args.id:
        parser.error("--s3 requires --id to be set")
    return args

def parse_srt(srt_path):
    encodings = ['utf-8', 'latin-1', 'utf-16', 'utf-32']
    for enc in encodings:
        try:
            with open(srt_path, 'r', encoding=enc) as file:
                content = file.read()
                break
        except Exception:
            continue
    else:
        console.print(f"[red]Cannot read SRT file: {srt_path}[/red]")
        sys.exit(1)

    pattern = re.compile(
        r'(\d+)\n'
        r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n'
        r'((?:.*\n)+?)\n',
        re.MULTILINE
    )

    return [
        (int(m.group(1)), m.group(2).replace(',', '.'), m.group(3).replace(',', '.'), m.group(4).replace('\n', ' ').strip())
        for m in pattern.finditer(content)
    ]

def get_complexity(text): return textstat.flesch_reading_ease(text)

def filter_dialogues(subtitles):
    important = []
    for idx, start, end, sentence in subtitles:
        words = nltk.word_tokenize(sentence)
        if len(words) >= 5:
            score = get_complexity(sentence)
            if score < 50:
                important.append({'index': idx, 'start': start, 'end': end, 'text': sentence, 'score': score})
    return important

def adjust_times(start, end):
    try:
        start_dt = datetime.strptime(start, "%H:%M:%S.%f")
        end_dt = datetime.strptime(end, "%H:%M:%S.%f")
    except ValueError:
        return start, end
    if (end_dt - start_dt).total_seconds() < 5:
        end_dt += timedelta(seconds=5)
    return start_dt.strftime("%H:%M:%S"), end_dt.strftime("%H:%M:%S")

def cut_video(movie, start, end, out_dir):
    start, end = adjust_times(start, end)
    output = os.path.join(out_dir, f"{uuid.uuid4()}.mp4")
    (
        ffmpeg
        .input(movie, ss=start, to=end)
        .output(output, vcodec='libx264', acodec='aac')
        .run(overwrite_output=True, quiet=True)
    )
    return output

def screenshot(video, out_dir):
    output = os.path.join(out_dir, f"{uuid.uuid4()}.jpg")
    (
        ffmpeg
        .input(video, ss=2)
        .output(output, vframes=1)
        .run(overwrite_output=True, quiet=True)
    )
    return output if os.path.exists(output) else None

def extract_audio(video, out_dir):
    output = os.path.join(out_dir, f"{uuid.uuid4()}.wav")
    (
        ffmpeg
        .input(video)
        .output(output, acodec='pcm_s16le')
        .run(overwrite_output=True, quiet=True)
    )
    return output if os.path.exists(output) else None

def save_to_csv(dialogues, srt_path):
    path = srt_path.replace('.srt', '_important.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['index', 'start', 'end', 'text', 'score'])
        writer.writeheader()
        writer.writerows(dialogues)
    console.print(f"[green]Saved important dialogues to {path}[/green]")

def main():
    display_ascii_art()
    args = parse_args()
    subs = parse_srt(args.srt)
    important = filter_dialogues(subs)
    save_to_csv(important, args.srt)

    output_dir = os.path.join(os.getcwd(), f"clips_{args.id or 'local'}")
    os.makedirs(output_dir, exist_ok=True)

    for d in tqdm(important, desc="Processing", unit="clip"):
        clip_path = cut_video(args.movie, d['start'], d['end'], output_dir)
        if args.screenshot:
            screenshot_path = screenshot(clip_path, output_dir)
            if screenshot_path:
                console.print(f"[blue]Screenshot: {screenshot_path}[/blue]")
        audio_path = extract_audio(clip_path, output_dir)
        if audio_path:
            console.print(f"[blue]Audio: {audio_path}[/blue]")

if __name__ == '__main__':
    main()
