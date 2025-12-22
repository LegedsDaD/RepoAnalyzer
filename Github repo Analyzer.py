import os, re, io, zipfile, requests
import tkinter as tk
from tkinter import messagebox
from collections import Counter
import lizard
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# ---------------- VISUAL HELPERS ----------------

def bar(percent, size=10):
    filled = int((percent / 100) * size)
    return "█" * filled + "░" * (size - filled)

# ---------------- LANGUAGE DETECTION ----------------

EXT_LANG = {
    ".py":"Python",".js":"JavaScript",".ts":"TypeScript",".java":"Java",
    ".cpp":"C++",".c":"C",".h":"C/C++ Header",".go":"Go",".rs":"Rust",
    ".php":"PHP",".rb":"Ruby",".swift":"Swift",".kt":"Kotlin",
    ".cs":"C#",".scala":"Scala",".r":"R",".m":"MATLAB",
    ".sh":"Shell",".html":"HTML",".css":"CSS",".json":"JSON",".yaml":"YAML"
}

# ---------------- GITHUB HELPERS ----------------

def repo_parts(url):
    parts = url.replace("https://github.com/","").split("/")
    return parts[0], parts[1]

def download_repo(owner, repo):
    url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall("temp_repo")
    return f"temp_repo/{repo}-main"

# ---------------- README CLEAN + SUMMARY ----------------

def clean_readme(text):
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)
    return text.strip()

def fetch_summary(owner, repo):
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
    r = requests.get(url)
    if r.status_code != 200:
        return "No README available."
    text = clean_readme(r.text)
    sents = re.split(r'(?<=[.!?]) +', text)
    if len(sents) < 5:
        return text[:500]
    tfidf = TfidfVectorizer(stop_words="english")
    X = tfidf.fit_transform(sents)
    scores = np.array(X.sum(axis=1)).flatten()
    top = sorted(zip(scores, sents), reverse=True)[:5]
    return " ".join(s for _, s in top)

# ---------------- ANALYSIS ----------------

def detect_languages(root):
    c = Counter()
    for r,_,files in os.walk(root):
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in EXT_LANG:
                c[EXT_LANG[ext]] += 1
    return c

def file_level_analysis(root):
    issues = []
    total_complexity = 0
    files = 0

    for r,_,fs in os.walk(root):
        for f in fs:
            path = os.path.join(r,f)

            if f.endswith(".py"):
                try:
                    a = lizard.analyze_file(path)
                    c = sum(fn.cyclomatic_complexity for fn in a.function_list)
                    total_complexity += c
                    files += 1
                    if c > 10:
                        issues.append(f"{f} → High complexity")
                except:
                    pass

            if os.path.getsize(path) > 200_000:
                issues.append(f"{f} → Very large file")

            if f.endswith(".py"):
                with open(path, errors="ignore") as fp:
                    if "def " in fp.read() and '"""' not in fp.read():
                        issues.append(f"{f} → Missing documentation")

    return issues, total_complexity, files

def health_score(root):
    score = 100
    missing = []
    for f,p in [("README.md",20),("LICENSE",10),("tests",15),(".github",10)]:
        if not os.path.exists(os.path.join(root,f)):
            score -= p
            missing.append(f)
    return max(score,0), missing

def test_coverage(root):
    src, tests = 0, 0
    for r,_,files in os.walk(root):
        for f in files:
            if f.endswith(".py"):
                if "test" in f.lower():
                    tests += 1
                else:
                    src += 1
    pct = int((tests / max(src,1)) * 100)
    level = "Low" if pct < 40 else "Medium" if pct < 70 else "High"
    return pct, level

def predict_trend(complexity, coverage):
    if complexity > 70 and coverage < 40:
        return "📉 Growing but risky (needs refactoring)"
    if complexity < 50 and coverage > 60:
        return "📈 Healthy and scalable"
    return "➡ Stable but could improve"

# ---------------- MAIN ----------------

def analyze_repo():
    url = repo_entry.get()
    mode = mode_var.get()

    if not url.startswith("https://github.com/"):
        messagebox.showerror("Error","Invalid GitHub URL")
        return

    owner, repo = repo_parts(url)
    output.delete("1.0",tk.END)

    root_path = download_repo(owner, repo)

    summary = fetch_summary(owner, repo)
    langs = detect_languages(root_path)
    issues, complexity, files = file_level_analysis(root_path)
    health, missing = health_score(root_path)
    coverage, cov_level = test_coverage(root_path)

    difficulty = min(int((complexity / max(files,1)) * 10),100)
    trend = predict_trend(difficulty, coverage)

    # -------- OUTPUT --------

    output.insert(tk.END,"📌 SUMMARY\n"+"-"*50+"\n"+summary+"\n\n")

    output.insert(tk.END,"📊 DASHBOARD\n")
    output.insert(tk.END,f"Code Difficulty   {bar(difficulty)} {difficulty}%\n")
    output.insert(tk.END,f"Project Health    {bar(health)} {health}%\n")
    output.insert(tk.END,f"Test Coverage     {bar(coverage)} {coverage}% ({cov_level})\n\n")

    output.insert(tk.END,"📂 LANGUAGES USED\n")
    for l,c in langs.items():
        output.insert(tk.END,f"• {l}: {c} files\n")

    output.insert(tk.END,f"\n📈 REPO TREND\n{trend}\n")

    if mode == "Advanced":
        output.insert(tk.END,"\n🔍 FILE-LEVEL INSIGHTS\n")
        if issues:
            for i in issues:
                output.insert(tk.END,f"• {i}\n")
        else:
            output.insert(tk.END,"• No major issues found\n")

        output.insert(tk.END,"\n🧠 REFACTOR SUGGESTIONS\n")
        if difficulty > 60:
            output.insert(tk.END,"• Break large functions into smaller ones\n")
        if coverage < 50:
            output.insert(tk.END,"• Add unit tests for critical logic\n")
        if missing:
            output.insert(tk.END,"• Add missing repo files: "+", ".join(missing)+"\n")

# ---------------- GUI ----------------

root = tk.Tk()
root.title("GitHub Repository Analyzer – Final")
root.geometry("900x650")

tk.Label(root,text="GitHub Repository URL").pack(pady=5)
repo_entry = tk.Entry(root,width=80)
repo_entry.pack()

mode_var = tk.StringVar(value="Beginner")
tk.Radiobutton(root,text="Beginner Mode",variable=mode_var,value="Beginner").pack()
tk.Radiobutton(root,text="Advanced Mode",variable=mode_var,value="Advanced").pack()

tk.Button(root,text="Run Analysis",command=analyze_repo).pack(pady=10)

output = tk.Text(root,wrap=tk.WORD)
output.pack(fill=tk.BOTH,expand=True,padx=10,pady=10)

root.mainloop()
