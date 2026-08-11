# MH + Central Govt Jobs — Free Auto-Sync Job Portal

Sirf Maharashtra aur Central Govt jobs dikhata hai — Job Title, Dept, Qualification,
Category, Last Date, Post, Location, Official Website, Apply Link, PDF Link.
Syllabus, Result, Admit Card, aur baaki states ka data isme nahi hai.

## Kaise deploy karein (10-15 min, 100% free)

### Step 1 — GitHub par push karo
1. https://github.com par naya **public repo** banao (e.g. `mh-central-jobs`)
2. Is poore folder ko us repo me push karo:
   ```
   git init
   git add .
   git commit -m "initial setup"
   git branch -M main
   git remote add origin https://github.com/<username>/<repo-name>.git
   git push -u origin main
   ```

### Step 2 — GitHub Pages on karo (website free hosting)
1. Repo -> **Settings** -> **Pages**
2. Source: **Deploy from a branch** -> Branch: `main` -> Folder: `/site`
3. Save karo. 1-2 min me `https://<username>.github.io/<repo-name>/` par site live ho jayegi.

### Step 3 — Auto-sync on karo (GitHub Actions)
Workflow file (`.github/workflows/sync-jobs.yml`) already repo me hai — kuch karna nahi hai,
GitHub khud din me 3 baar (8AM, 2PM, 8PM IST) scraper chalayega aur `site/jobs.json` update
karke commit kar dega. Website apne aap naya data dikhane lagegi.

**Permission check:** Settings -> Actions -> General -> "Workflow permissions" me
**"Read and write permissions"** select karo (varna auto-commit fail hoga).

### Step 4 (optional) — Pehli baar manually chalao
Repo -> **Actions** tab -> "Sync Jobs (Maharashtra + Central)" -> **Run workflow** button.
Isse turant pehla data aa jayega, warna agle scheduled run tak wait karna padega.

## Local par test karna (deploy se pehle)
```
cd scraper
pip install -r requirements.txt
python scrape.py
```
Ye `site/jobs.json` bana dega. Phir `site/index.html` ko browser me kholo (ya `python -m http.server`
site folder ke andar chalao) — data turant dikhega.

## Structure
```
scraper/
  scrape.py          <- Maharashtra + Central jobs scrape karta hai
  requirements.txt
site/
  index.html         <- Website (jobs.json padhta hai)
  jobs.json           <- Data (auto-update hota hai)
.github/workflows/
  sync-jobs.yml       <- Cron job (free GitHub Actions)
```

## Zaroori Note
FreeJobAlert.com ka koi official public API nahi hai, isliye ye unki website se data
"scrape" (parse) karta hai. Unke Terms of Service ke against ja sakta hai, aur agar
unka page-structure kabhi badla to scraper ko update karna padega. Scraper me 1-second
delay bhi rakha hai taaki unke server par extra load na pade.
