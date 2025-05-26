## 🎬 FilmFluency CLI

Extract **important, complex dialogue clips** from any movie using its subtitle file. Designed for non-tech users with a smooth command-line experience using `tqdm` and `rich`.

---

### ✅ Features

* Parses `.srt` subtitle files.
* Analyzes sentence complexity with **Flesch Reading Ease**.
* Extracts meaningful dialogue clips using `ffmpeg`.
* Optionally generates screenshots and audio files.
* CLI progress and colorful output.
* Clean, minimal setup. No Django required.

---

### 🚀 Quick Start

#### 1. Clone this repo

```bash
git clone https://github.com/BDR-Pro/Film-Fluency-Cli.git
cd Film-Fluency-Cli
```

#### 2. Install dependencies

Make sure Python 3.8+ is installed. Then run:

```bash
pip install -r requirements.txt
```

#### 3. Install FFmpeg

This tool depends on the system-level `ffmpeg` binary.

* [Download FFmpeg](https://ffmpeg.org/download.html)
* On macOS: `brew install ffmpeg`
* On Ubuntu: `sudo apt install ffmpeg`

---

### 🛠️ Usage

```bash
python filmfluency_cli.py --movie path/to/movie.mp4 --srt path/to/subtitles.srt
```

#### Optional flags

* `--screenshot`: Save a screenshot for each clip.
* `--s3 URL`: Enable S3 upload (requires `--id`).
* `--id`: ID of the movie (used with S3 upload).

---

### 📁 Output

Clips, screenshots (if selected), and audio files will be saved in:

```
./clips_<movie_id or 'local'>/
```

A CSV file with all selected dialogues will be saved as:

```
subtitles_important.csv
```

---

### 💡 Example

```bash
python filmfluency_cli.py \
  --movie "The Matrix.mp4" \
  --srt "The Matrix.srt" \
  --screenshot
```

---

### 🧪 Testing

Want to test this tool? Provide any `.mp4` and `.srt` pair, then check the generated folder and CSV file.

---

Let me know if you want to add **unit testing instructions**, a **sample input set**, or **S3 upload integration** next.
