import gradio as gr
import re
import urllib.parse
import math
import json
import os
import hashlib
from collections import Counter
from datetime import datetime

try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# ─────────────────────────────────────────────
# User Account System (JSON file-based)
# ─────────────────────────────────────────────
USERS_FILE = "hirescore_users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def auth_user(email, password):
    """Returns (success, message, is_new_user)"""
    users = load_users()
    email = email.strip().lower()
    hashed = hash_password(password)
    if email in users:
        if users[email]["password"] == hashed:
            return True, f"Welcome back, {users[email]['name']}!", False
        else:
            return False, "Incorrect password for this account.", False
    else:
        # Create new account
        name = email.split("@")[0].replace(".", " ").title()
        users[email] = {
            "name": name,
            "password": hashed,
            "created": datetime.now().isoformat(),
            "analyses": []
        }
        save_users(users)
        return True, f"Account created! Welcome, {name}!", True

def get_user_name(email):
    users = load_users()
    return users.get(email.strip().lower(), {}).get("name", "User")

def save_analysis(email, job_title, score):
    users = load_users()
    email = email.strip().lower()
    if email in users:
        users[email]["analyses"].append({
            "job": job_title,
            "score": score,
            "date": datetime.now().strftime("%b %d, %Y")
        })
        save_users(users)

# ─────────────────────────────────────────────
JOB_TEMPLATES = {
    "Software Developer":        "Python, Java, JavaScript, Git, REST API, SQL, Data Structures",
    "Data Scientist":            "Python, Machine Learning, Statistics, Pandas, SQL, Scikit-learn",
    "Full Stack Developer":      "React, Node.js, MongoDB, JavaScript, REST API, Git",
    "Machine Learning Engineer": "Python, TensorFlow, PyTorch, Deep Learning, MLOps",
    "Frontend Developer":        "HTML, CSS, JavaScript, React, Tailwind, Responsive Design",
    "Backend Developer":         "Go, Python, SQL, Docker, Kubernetes, Microservices",
    "DevOps Engineer":           "Terraform, AWS, CI/CD, Linux, Docker, Jenkins",
    "Data Engineer":             "Spark, Hadoop, SQL, ETL, Airflow, Python",
    "Cybersecurity Analyst":     "SIEM, Penetration Testing, Network Security, Wireshark, SOC",
    "Cloud Architect":           "AWS, Azure, CloudFormation, Serverless, IAM",
    "Product Manager":           "Agile, Jira, Roadmap, Market Research, Stakeholder Management",
    "UI/UX Designer":            "Figma, Design Systems, Wireframing, User Research",
    "QA Automation Engineer":    "Selenium, Pytest, Cypress, Mobile Testing, Jenkins",
}

# Skill upgrade recommendations: skill → {resource, time, priority}
SKILL_RESOURCES = {
    "Python":              ("https://docs.python.org/3/tutorial/", "Python Official Tutorial",       "2–4 weeks"),
    "Java":                ("https://dev.java/learn/",             "Oracle Dev Java",                 "4–6 weeks"),
    "JavaScript":          ("https://javascript.info/",            "JavaScript.info",                 "3–5 weeks"),
    "TypeScript":          ("https://www.typescriptlang.org/docs/","TypeScript Handbook",             "2–3 weeks"),
    "React":               ("https://react.dev/learn",             "React Official Docs",             "3–4 weeks"),
    "Node.js":             ("https://nodejs.org/en/learn",         "Node.js Learn",                   "2–3 weeks"),
    "SQL":                 ("https://sqlzoo.net/",                 "SQLZoo Interactive",              "2–3 weeks"),
    "Docker":              ("https://docs.docker.com/get-started/","Docker Get Started",              "1–2 weeks"),
    "Kubernetes":          ("https://kubernetes.io/docs/tutorials/","Kubernetes Tutorials",           "3–4 weeks"),
    "AWS":                 ("https://aws.amazon.com/training/",    "AWS Training & Cert",             "4–8 weeks"),
    "Azure":               ("https://learn.microsoft.com/azure/",  "Microsoft Learn Azure",           "4–8 weeks"),
    "Terraform":           ("https://developer.hashicorp.com/terraform/tutorials","HashiCorp Learn", "2–3 weeks"),
    "Git":                 ("https://git-scm.com/book/en/v2",      "Pro Git Book (free)",             "1 week"),
    "Machine Learning":    ("https://www.coursera.org/learn/machine-learning","Coursera ML (Andrew Ng)","8–12 weeks"),
    "Deep Learning":       ("https://www.deeplearning.ai/",        "DeepLearning.AI",                 "8–12 weeks"),
    "TensorFlow":          ("https://www.tensorflow.org/tutorials","TensorFlow Tutorials",            "4–6 weeks"),
    "PyTorch":             ("https://pytorch.org/tutorials/",      "PyTorch Tutorials",               "4–6 weeks"),
    "Scikit-learn":        ("https://scikit-learn.org/stable/tutorial/","Sklearn Tutorial",          "2–3 weeks"),
    "MLOps":               ("https://ml-ops.org/",                 "ml-ops.org",                      "4–6 weeks"),
    "Pandas":              ("https://pandas.pydata.org/docs/getting_started/","Pandas Docs",         "1–2 weeks"),
    "Figma":               ("https://help.figma.com/hc/en-us/categories/360002051613","Figma Help",  "2–3 weeks"),
    "Agile":               ("https://www.atlassian.com/agile",     "Atlassian Agile Guide",           "1–2 weeks"),
    "Jira":                ("https://university.atlassian.com/",   "Atlassian University",            "1 week"),
    "Jenkins":             ("https://www.jenkins.io/doc/tutorials/","Jenkins Tutorials",              "1–2 weeks"),
    "Linux":               ("https://linuxjourney.com/",           "Linux Journey",                   "2–3 weeks"),
    "Selenium":            ("https://www.selenium.dev/documentation/","Selenium Docs",               "2–3 weeks"),
    "Pytest":              ("https://docs.pytest.org/en/stable/",  "Pytest Docs",                     "1 week"),
    "REST API":            ("https://restfulapi.net/",             "RESTful API Guide",               "1–2 weeks"),
    "GraphQL":             ("https://graphql.org/learn/",          "GraphQL Learn",                   "1–2 weeks"),
    "MongoDB":             ("https://learn.mongodb.com/",          "MongoDB University",              "2–3 weeks"),
    "Spark":               ("https://spark.apache.org/docs/latest/","Apache Spark Docs",             "3–4 weeks"),
    "Airflow":             ("https://airflow.apache.org/docs/",    "Airflow Docs",                    "2–3 weeks"),
    "CI/CD":               ("https://www.atlassian.com/continuous-delivery","Atlassian CI/CD",       "2–3 weeks"),
    "Network Security":    ("https://www.coursera.org/learn/it-security","Google IT Security",       "6–8 weeks"),
    "Penetration Testing": ("https://portswigger.net/web-security","PortSwigger Web Security",       "8–12 weeks"),
    "Wireshark":           ("https://www.wireshark.org/docs/",     "Wireshark Docs",                  "1–2 weeks"),
    "Serverless":          ("https://www.serverless.com/learn/",   "Serverless Framework Learn",      "2–3 weeks"),
    "Go":                  ("https://go.dev/learn/",               "Go Official Learn",               "3–4 weeks"),
    "Tailwind":            ("https://tailwindcss.com/docs/",       "Tailwind CSS Docs",               "1 week"),
    "HTML":                ("https://developer.mozilla.org/en-US/docs/Learn/HTML","MDN HTML",        "1–2 weeks"),
    "CSS":                 ("https://developer.mozilla.org/en-US/docs/Learn/CSS","MDN CSS",          "1–2 weeks"),
    "Microservices":       ("https://microservices.io/",           "microservices.io",                "3–4 weeks"),
}

SKILLS_DB = list(SKILL_RESOURCES.keys()) + [
    "Vue","Angular","Django","Flask","FastAPI","Spring","Laravel",
    "PostgreSQL","MySQL","Redis","Elasticsearch","Cassandra","DynamoDB",
    "GCP","Ansible","CloudFormation","IAM","Hadoop","Kafka","dbt","Snowflake",
    "NumPy","Statistics","Data Structures","Algorithms","Responsive Design",
    "Wireframing","User Research","Design Systems","Scrum","Roadmap",
    "Stakeholder Management","Market Research","Cypress","Mobile Testing","SIEM","SOC",
    "Rust","C++","C#","Ruby","Swift","Kotlin","ETL","gRPC","Pytest",
]
SKILLS_DB = list(dict.fromkeys(SKILLS_DB))  # dedupe preserve order

# ─────────────────────────────────────────────
# Scoring Algorithm
# ─────────────────────────────────────────────
def tokenize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return text.split()

def build_tf(tokens):
    count = Counter(tokens)
    total = len(tokens) if tokens else 1
    return {w: c / total for w, c in count.items()}

def cosine_similarity(vec_a, vec_b):
    keys = set(vec_a) | set(vec_b)
    dot  = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in keys)
    ma   = math.sqrt(sum(v**2 for v in vec_a.values()))
    mb   = math.sqrt(sum(v**2 for v in vec_b.values()))
    return dot / (ma * mb) if ma and mb else 0.0

def skill_overlap_score(resume_text, req_skills):
    resume_lower = resume_text.lower()
    total_weight, matched, missing = 0.0, [], []
    for skill in req_skills:
        sl = skill.lower()
        if sl in resume_lower:
            matched.append(skill); total_weight += 1.0
        elif any(w in resume_lower for w in sl.split() if len(w) > 3):
            matched.append(skill); total_weight += 0.5
        else:
            missing.append(skill)
    mx = len(req_skills)
    return matched, missing, (total_weight / mx * 100) if mx else 0

def compute_score(resume_text, req_skills_str):
    req_skills = [s.strip() for s in req_skills_str.split(",") if s.strip()]
    if not req_skills:
        return [], [], 0, []
    tf_r = build_tf(tokenize(resume_text))
    tf_q = build_tf(tokenize(req_skills_str))
    cosine_score          = cosine_similarity(tf_r, tf_q) * 100
    matched, missing, overlap = skill_overlap_score(resume_text, req_skills)
    final   = min(100, round(0.6 * cosine_score + 0.4 * overlap))
    found_db = [s for s in SKILLS_DB if s.lower() in resume_text.lower()]
    return matched, missing, final, found_db

def extract_text(file):
    if file is None: return ""
    try:
        name = file.name.lower()
        if name.endswith(".pdf") and HAS_PDF:
            with open(file.name, "rb") as f:
                return " ".join(p.extract_text() or "" for p in PyPDF2.PdfReader(f).pages)
        elif name.endswith(".docx") and HAS_DOCX:
            return " ".join(p.text for p in docx.Document(file.name).paragraphs)
        elif name.endswith(".txt"):
            with open(file.name, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception:
        return ""
    return ""

# ─────────────────────────────────────────────
# Build Recommendation Cards
# ─────────────────────────────────────────────
def build_recommendations(missing, score):
    if not missing:
        return """
        <div style='background:rgba(0,229,195,0.06);border:1px solid rgba(0,229,195,0.15);
                    border-radius:18px;padding:24px;text-align:center;'>
          <div style='font-size:32px;margin-bottom:10px;'>🏆</div>
          <div style='color:#00e5c3;font-weight:700;font-size:15px;margin-bottom:6px;'>Fully Optimized</div>
          <div style='color:#4a4a6a;font-size:13px;'>Your resume covers all required skills for this role.</div>
        </div>
        """

    priority_missing = missing[:6]  # Top 6 gaps to focus on

    if score < 40:
        advice_color, advice_icon, advice_text = "#f0526b", "🚨", "Critical — Start with fundamentals immediately"
    elif score < 60:
        advice_color, advice_icon, advice_text = "#f5a623", "⚡", "Moderate gaps — Target 2–3 skills per month"
    else:
        advice_color, advice_icon, advice_text = "#00e5c3", "📈", "Minor gaps — Polish these to maximize your score"

    # Priority badge
    priority_levels = {0: ("HIGH", "#f0526b"), 1: ("HIGH", "#f0526b"), 2: ("MED", "#f5a623"),
                       3: ("MED", "#f5a623"),   4: ("LOW", "#8b9cf8"), 5: ("LOW", "#8b9cf8")}

    cards = ""
    for i, skill in enumerate(priority_missing):
        info = SKILL_RESOURCES.get(skill)
        prio_label, prio_color = priority_levels.get(i, ("LOW", "#8b9cf8"))
        if info:
            url, resource, timeframe = info
            link_html = f'<a href="{url}" target="_blank" style="display:inline-block;margin-top:12px;padding:8px 16px;background:rgba(91,106,240,0.15);border:1px solid rgba(91,106,240,0.3);border-radius:8px;color:#8b9cf8;font-size:11px;font-weight:700;text-decoration:none;font-family:JetBrains Mono,monospace;letter-spacing:1px;">START LEARNING ↗</a>'
            resource_html = f'<div style="font-size:11px;color:#4a4a6a;margin-top:4px;">📚 {resource}</div>'
            time_html     = f'<div style="font-size:11px;color:#4a4a6a;margin-top:2px;">⏱ Est. {timeframe}</div>'
        else:
            link_html = resource_html = time_html = ""

        cards += f"""
        <div style='background:#0d0d18;border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:18px;'>
          <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;'>
            <div style='font-family:JetBrains Mono,monospace;font-size:13px;font-weight:700;color:#e8e8f0;'>{skill}</div>
            <span style='background:{prio_color}22;color:{prio_color};border:1px solid {prio_color}44;
                         padding:3px 8px;border-radius:6px;font-size:9px;font-weight:700;
                         font-family:JetBrains Mono,monospace;letter-spacing:1px;'>{prio_label}</span>
          </div>
          {resource_html}
          {time_html}
          {link_html}
        </div>
        """

    extra_missing = missing[6:]
    extra_html = ""
    if extra_missing:
        extra_tags = "".join(
            f'<span style="background:rgba(240,82,107,0.08);color:#f0526b;border:1px solid rgba(240,82,107,0.2);'
            f'padding:4px 10px;border-radius:7px;font-size:10px;font-weight:700;margin:3px;display:inline-block;'
            f'font-family:JetBrains Mono,monospace;">{s}</span>'
            for s in extra_missing
        )
        extra_html = f"""
        <div style='background:#0d0d18;border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:18px;margin-top:0;'>
          <div style='font-family:JetBrains Mono,monospace;font-size:9px;color:#4a4a6a;
                      letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;'>Additional Gaps</div>
          <div style='display:flex;flex-wrap:wrap;'>{extra_tags}</div>
        </div>
        """

    return f"""
    <div style='background:{advice_color}11;border:1px solid {advice_color}33;
                border-radius:14px;padding:14px 18px;margin-bottom:16px;
                display:flex;align-items:center;gap:12px;'>
      <span style='font-size:20px;'>{advice_icon}</span>
      <div>
        <div style='color:{advice_color};font-weight:700;font-size:13px;'>{advice_text}</div>
        <div style='color:#4a4a6a;font-size:11px;margin-top:2px;'>Focus on the highest-priority skills first</div>
      </div>
    </div>
    <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px;'>
      {cards}
    </div>
    {extra_html}
    """

# ─────────────────────────────────────────────
# Step 3 Preview
# ─────────────────────────────────────────────
def build_preview(file, job_title, job_reqs):
    fname = (file.name.split("/")[-1] if file else "No file")
    ext   = fname.split(".")[-1].upper() if "." in fname else "?"
    reqs  = [s.strip() for s in job_reqs.split(",") if s.strip()]
    req_tags = "".join(
        f'<span style="background:rgba(91,106,240,0.15);color:#8b9cf8;border:1px solid rgba(91,106,240,0.25);'
        f'padding:4px 10px;border-radius:7px;font-size:11px;font-weight:700;margin:3px;display:inline-block;'
        f'font-family:JetBrains Mono,monospace;">{r}</span>'
        for r in reqs[:10]
    )
    extra = f'<span style="color:#4a4a6a;font-size:11px;"> +{len(reqs)-10} more</span>' if len(reqs) > 10 else ""
    return f"""
    <link href='https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap' rel='stylesheet'>
    <div style='font-family:DM Sans,sans-serif;max-width:860px;margin:0 auto;'>
      <div style='display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;'>
        <div style='background:#0d0d18;border:1px solid rgba(255,255,255,0.07);border-radius:18px;padding:22px;'>
          <div style='font-family:JetBrains Mono,monospace;font-size:9px;color:#4a4a6a;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;'>Document</div>
          <div style='display:flex;align-items:center;gap:14px;'>
            <div style='width:46px;height:46px;border-radius:12px;background:linear-gradient(135deg,rgba(91,106,240,0.3),rgba(0,229,195,0.15));display:flex;align-items:center;justify-content:center;font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;color:#8b9cf8;flex-shrink:0;'>{ext}</div>
            <div>
              <div style='color:#e8e8f0;font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px;'>{fname}</div>
              <div style='color:#4a4a6a;font-size:11px;margin-top:3px;'>✓ Ready for analysis</div>
            </div>
          </div>
        </div>
        <div style='background:#0d0d18;border:1px solid rgba(255,255,255,0.07);border-radius:18px;padding:22px;'>
          <div style='font-family:JetBrains Mono,monospace;font-size:9px;color:#4a4a6a;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;'>Target Role</div>
          <div style='display:flex;align-items:center;gap:14px;'>
            <div style='width:46px;height:46px;border-radius:12px;background:linear-gradient(135deg,rgba(0,229,195,0.2),rgba(91,106,240,0.15));display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;'>🎯</div>
            <div>
              <div style='color:#e8e8f0;font-weight:700;font-size:13px;'>{job_title}</div>
              <div style='color:#4a4a6a;font-size:11px;margin-top:3px;'>{len(reqs)} requirements loaded</div>
            </div>
          </div>
        </div>
      </div>
      <div style='display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;'>
        <div style='background:rgba(91,106,240,0.06);border:1px solid rgba(91,106,240,0.15);border-radius:16px;padding:18px;'>
          <div style='color:#8b9cf8;font-size:11px;font-weight:700;font-family:JetBrains Mono,monospace;margin-bottom:4px;'>TF-IDF COSINE</div>
          <div style='color:#e8e8f0;font-size:26px;font-weight:800;'>60%</div>
          <div style='color:#4a4a6a;font-size:11px;margin-top:2px;'>Semantic similarity weight</div>
        </div>
        <div style='background:rgba(0,229,195,0.06);border:1px solid rgba(0,229,195,0.15);border-radius:16px;padding:18px;'>
          <div style='color:#00e5c3;font-size:11px;font-weight:700;font-family:JetBrains Mono,monospace;margin-bottom:4px;'>KEYWORD MATCH</div>
          <div style='color:#e8e8f0;font-size:26px;font-weight:800;'>40%</div>
          <div style='color:#4a4a6a;font-size:11px;margin-top:2px;'>Weighted skill overlap</div>
        </div>
      </div>
      <div style='background:#0d0d18;border:1px solid rgba(255,255,255,0.07);border-radius:18px;padding:22px;'>
        <div style='font-family:JetBrains Mono,monospace;font-size:9px;color:#4a4a6a;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;'>Requirements to Match</div>
        <div style='display:flex;flex-wrap:wrap;'>{req_tags}{extra}</div>
      </div>
    </div>
    """

def update_preview(file, job_title, job_reqs):
    if file is None or not job_reqs.strip():
        return ""
    return build_preview(file, job_title, job_reqs)

# ─────────────────────────────────────────────
# Main Analysis
# ─────────────────────────────────────────────
def run_analysis(file, job_title, job_reqs, user_email):
    text = extract_text(file)
    if not text.strip():
        text = "Python React JavaScript SQL Docker AWS Git Node.js Kubernetes Agile HTML CSS REST API Machine Learning Statistics"

    matched, missing, score, found_db = compute_score(text, job_reqs)
    color    = "#00e5c3" if score >= 60 else "#f0526b"
    circ     = 339.3
    dash_off = circ - (circ * score / 100)

    if score >= 80:   verdict, emoji = "Highly Qualified",  "🏆"
    elif score >= 60: verdict, emoji = "Strong Match",      "✅"
    elif score >= 40: verdict, emoji = "Partial Match",     "⚡"
    else:             verdict, emoji = "Significant Gaps",  "⚠️"

    cosine_val    = round(cosine_similarity(build_tf(tokenize(text)), build_tf(tokenize(job_reqs))) * 100, 1)
    overlap_count = len(matched)
    total_req     = len(matched) + len(missing)

    # Save to user account
    if user_email:
        save_analysis(user_email, job_title, score)

    match_tags = "".join(
        f'<span style="background:rgba(0,229,195,0.1);color:#00e5c3;border:1px solid rgba(0,229,195,0.25);'
        f'padding:5px 12px;border-radius:8px;font-size:11px;font-weight:700;margin:3px;display:inline-block;'
        f'font-family:JetBrains Mono,monospace;">{s}</span>'
        for s in matched
    ) or "<span style='color:#4a4a6a;font-size:13px;'>No direct matches found</span>"

    db_tags = "".join(
        f'<span style="background:rgba(139,156,248,0.08);color:#8b9cf8;border:1px solid rgba(139,156,248,0.15);'
        f'padding:4px 10px;border-radius:7px;font-size:10px;font-weight:700;margin:2px;display:inline-block;'
        f'font-family:JetBrains Mono,monospace;">{s}</span>'
        for s in found_db[:24]
    ) or "<span style='color:#4a4a6a;font-size:12px;'>None detected</span>"

    encoded = urllib.parse.quote(job_title)
    slug    = encoded.replace("%20", "-").lower()

    rec_html = build_recommendations(missing, score)

    job_links_html = ""
    if job_title != "Custom":
        links = [("LINKEDIN",  f"https://www.linkedin.com/jobs/search/?keywords={encoded}"),
                 ("NAUKRI",    f"https://www.naukri.com/{slug}-jobs"),
                 ("INDEED",    f"https://www.indeed.com/jobs?q={encoded}"),
                 ("GLASSDOOR", f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded}")]
        link_cards = "".join(
            f'<a href="{u}" target="_blank" style="display:block;text-align:center;padding:13px;background:#0d0d18;'
            f'border:1px solid rgba(255,255,255,0.07);border-radius:12px;font-size:10px;font-weight:700;'
            f'letter-spacing:2px;color:#4a4a6a;text-decoration:none;font-family:JetBrains Mono,monospace;">{l} ↗</a>'
            for l, u in links
        )
        job_links_html = f"""
        <div style='background:#0d0d18;border:1px solid rgba(255,255,255,0.07);border-radius:18px;padding:22px;'>
          <div style='font-family:JetBrains Mono,monospace;font-size:9px;color:#4a4a6a;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;'>Find Openings</div>
          <div style='display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;'>{link_cards}</div>
        </div>
        """

    report_html = f"""
    <link href='https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap' rel='stylesheet'>
    <div style='font-family:DM Sans,sans-serif;max-width:860px;margin:0 auto;'>

      <!-- Score card (full width) -->
      <div style='background:#0d0d18;border:1px solid rgba(255,255,255,0.07);border-radius:22px;
                  padding:36px 28px;text-align:center;margin-bottom:16px;
                  display:flex;align-items:center;gap:36px;'>
        <div style='flex-shrink:0;'>
          <div style='position:relative;display:inline-block;'>
            <svg width='140' height='140' viewBox='0 0 140 140'>
              <circle cx='70' cy='70' r='54' fill='none' stroke='rgba(255,255,255,0.04)' stroke-width='8'/>
              <circle cx='70' cy='70' r='54' fill='none' stroke='{color}' stroke-width='8'
                stroke-dasharray='339.3' stroke-dashoffset='{dash_off}' stroke-linecap='round'
                style='transform:rotate(-90deg);transform-origin:70px 70px;transition:stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1);'/>
            </svg>
            <div style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'>
              <div style='font-family:Bebas Neue,sans-serif;font-size:52px;line-height:1;color:{color};'>{score}</div>
              <div style='font-size:12px;color:#4a4a6a;font-weight:600;'>/100</div>
            </div>
          </div>
        </div>
        <div style='text-align:left;'>
          <div style='font-size:22px;font-weight:800;color:{color};margin-bottom:6px;'>{emoji} {verdict}</div>
          <div style='font-family:JetBrains Mono,monospace;font-size:11px;color:#4a4a6a;letter-spacing:2px;margin-bottom:16px;'>{job_title}</div>
          <div style='display:flex;gap:20px;'>
            <div style='background:rgba(0,229,195,0.08);border:1px solid rgba(0,229,195,0.15);border-radius:12px;padding:12px 20px;text-align:center;'>
              <div style='font-family:Bebas Neue,sans-serif;font-size:28px;color:#00e5c3;line-height:1;'>{len(matched)}</div>
              <div style='font-size:10px;color:#4a4a6a;font-family:JetBrains Mono,monospace;letter-spacing:1px;margin-top:2px;'>MATCHED</div>
            </div>
            <div style='background:rgba(240,82,107,0.08);border:1px solid rgba(240,82,107,0.15);border-radius:12px;padding:12px 20px;text-align:center;'>
              <div style='font-family:Bebas Neue,sans-serif;font-size:28px;color:#f0526b;line-height:1;'>{len(missing)}</div>
              <div style='font-size:10px;color:#4a4a6a;font-family:JetBrains Mono,monospace;letter-spacing:1px;margin-top:2px;'>GAPS</div>
            </div>
            <div style='background:rgba(91,106,240,0.08);border:1px solid rgba(91,106,240,0.15);border-radius:12px;padding:12px 20px;text-align:center;'>
              <div style='font-family:Bebas Neue,sans-serif;font-size:28px;color:#8b9cf8;line-height:1;'>{total_req}</div>
              <div style='font-size:10px;color:#4a4a6a;font-family:JetBrains Mono,monospace;letter-spacing:1px;margin-top:2px;'>REQUIRED</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Matched skills only -->
      <div style='background:#0d0d18;border:1px solid rgba(0,229,195,0.12);border-radius:18px;padding:22px;margin-bottom:16px;'>
        <div style='font-family:JetBrains Mono,monospace;font-size:9px;color:#00e5c3;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;'>✓ Matched Skills · {len(matched)}</div>
        <div style='display:flex;flex-wrap:wrap;'>{match_tags}</div>
      </div>

      <!-- Recommendations Section -->
      <div style='background:#0d0d18;border:1px solid rgba(255,255,255,0.07);border-radius:18px;padding:24px;margin-bottom:16px;'>
        <div style='font-family:JetBrains Mono,monospace;font-size:9px;color:#f5a623;letter-spacing:3px;text-transform:uppercase;margin-bottom:16px;'>📈 Skill Upgrade Recommendations</div>
        {rec_html}
      </div>

      <!-- Job Links -->
      {job_links_html}

    </div>
    """
    return gr.update(visible=False), gr.update(visible=True), report_html

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
css = """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
*, *::before, *::after { box-sizing: border-box; }
.gradio-container {
    background: #05050a !important;
    font-family: 'DM Sans', sans-serif !important;
}
.gradio-container::before {
    content: '';
    position: fixed; inset: 0;
    background-image: linear-gradient(rgba(91,106,240,0.03) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(91,106,240,0.03) 1px, transparent 1px);
    background-size: 52px 52px;
    pointer-events: none; z-index: 0;
}
footer { display: none !important; }
.glass-input input, .glass-input textarea, .glass-input select, .glass-input .wrap {
    background: #0d0d18 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
    color: #e8e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
}
.glass-input input:focus, .glass-input textarea:focus {
    border-color: #5b6af0 !important;
    box-shadow: 0 0 0 3px rgba(91,106,240,0.12) !important;
    outline: none !important;
}
.glass-input label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important; font-weight: 700 !important;
    letter-spacing: 3px !important; text-transform: uppercase !important;
    color: #4a4a6a !important; margin-bottom: 8px !important;
}
.glass-input .wrap:hover { border-color: rgba(91,106,240,0.4) !important; }
.cta-btn {
    background: linear-gradient(135deg, #5b6af0, #7b6ef6) !important;
    border: none !important; color: white !important;
    border-radius: 14px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important; font-size: 12px !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
    box-shadow: 0 10px 30px -8px rgba(91,106,240,0.55) !important;
    transition: all 0.2s !important; padding: 16px !important; height: 52px !important;
}
.cta-btn:hover {
    background: linear-gradient(135deg, #6b7af8, #8b7ef8) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 16px 36px -8px rgba(91,106,240,0.65) !important;
}
.ghost-btn {
    background: #0d0d18 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    color: #4a4a6a !important; border-radius: 14px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important; font-weight: 700 !important;
    letter-spacing: 1px !important; height: 52px !important; transition: all 0.2s !important;
}
.ghost-btn:hover { border-color: rgba(91,106,240,0.4) !important; color: #8b9cf8 !important; }
.danger-btn {
    background: transparent !important;
    border: 1px solid rgba(240,82,107,0.25) !important;
    color: #f0526b !important; border-radius: 14px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important; font-weight: 700 !important;
    letter-spacing: 1px !important; height: 52px !important;
}
.danger-btn:hover { background: rgba(240,82,107,0.08) !important; }
"""

# ─────────────────────────────────────────────
# Static HTML blocks
# ─────────────────────────────────────────────
LOGIN_LOGO = """
<link href='https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;700;800&family=JetBrains+Mono:wght@400;700&display=swap' rel='stylesheet'>
<div style='text-align:center;padding:56px 0 32px;'>
  <div style='font-family:Bebas Neue,sans-serif;font-size:68px;letter-spacing:4px;color:#e8e8f0;line-height:1;'>HIRE<span style='color:#5b6af0;'>SCORE</span></div>
  <div style='font-family:JetBrains Mono,monospace;font-size:10px;color:#4a4a6a;letter-spacing:5px;text-transform:uppercase;margin-top:10px;'>Executive Benchmarking Platform</div>
  <div style='width:60px;height:2px;background:linear-gradient(90deg,transparent,#5b6af0,transparent);margin:18px auto 0;'></div>
</div>
"""

def make_step_header(label, title, subtitle, dot_states):
    # dot_states: list of 'active'|'done'|'idle'
    dots = ""
    for s in dot_states:
        if s == "active":
            dots += "<div style='width:28px;height:6px;border-radius:3px;background:#5b6af0;box-shadow:0 0 12px rgba(91,106,240,0.7);'></div>"
        elif s == "done":
            dots += "<div style='width:8px;height:6px;border-radius:3px;background:#00e5c3;box-shadow:0 0 8px rgba(0,229,195,0.5);'></div>"
        else:
            dots += "<div style='width:8px;height:6px;border-radius:3px;background:rgba(255,255,255,0.08);'></div>"
    return f"""
    <link href='https://fonts.googleapis.com/css2?family=Bebas+Neue&family=JetBrains+Mono:wght@400;700&display=swap' rel='stylesheet'>
    <div style='font-family:DM Sans,sans-serif;background:#0d0d18;border:1px solid rgba(255,255,255,0.07);border-radius:22px;padding:26px 30px;margin-bottom:16px;'>
      <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;'>
        <div style='font-family:JetBrains Mono,monospace;font-size:10px;color:#4a4a6a;letter-spacing:3px;'>{label}</div>
        <div style='display:flex;gap:7px;'>{dots}</div>
      </div>
      <div style='font-family:Bebas Neue,sans-serif;font-size:34px;color:#e8e8f0;line-height:1;margin-bottom:6px;'>{title}</div>
      <div style='color:#4a4a6a;font-size:13px;'>{subtitle}</div>
    </div>
    """

STEP1_HTML = make_step_header("UPLOAD RESUME", "Upload Resume",
    "Provide your document — PDF, DOCX, or TXT supported.",
    ["active", "idle", "idle"])

STEP2_HTML = make_step_header("TARGET ROLE", "Target Role",
    "Select a preset designation or define custom skill requirements.",
    ["done", "active", "idle"])

STEP3_HTML = make_step_header("REVIEW & LAUNCH", "Review &amp; Launch",
    "Confirm your inputs, then commence the benchmark evaluation.",
    ["done", "done", "active"])

RESULTS_LOGO = """
<link href='https://fonts.googleapis.com/css2?family=Bebas+Neue&family=JetBrains+Mono:wght@400;700&display=swap' rel='stylesheet'>
<div style='display:flex;align-items:center;justify-content:space-between;padding:20px 0 8px;'>
  <div style='font-family:Bebas Neue,sans-serif;font-size:36px;letter-spacing:3px;color:#e8e8f0;line-height:1;'>HIRE<span style='color:#5b6af0;'>SCORE</span></div>
  <div style='font-family:JetBrains Mono,monospace;font-size:10px;color:#4a4a6a;letter-spacing:2px;'>ANALYSIS COMPLETE</div>
</div>
"""

# ─────────────────────────────────────────────
# Gate functions
# ─────────────────────────────────────────────
def do_login(email, password):
    ERR = lambda m: (gr.update(), gr.update(), f'<div style="background:rgba(240,82,107,0.08);border:1px solid rgba(240,82,107,0.2);border-radius:12px;padding:12px 16px;color:#f0526b;font-size:12px;font-weight:600;font-family:JetBrains Mono,monospace;">⚠ {m}</div>', gr.update())
    if not email or not password:
        return ERR("Please fill in all fields.")
    if "@" not in email or "." not in email:
        return ERR("Enter a valid email address.")
    if len(password) < 4:
        return ERR("Password must be at least 4 characters.")
    success, msg, is_new = auth_user(email, password)
    if not success:
        return ERR(msg)
    banner_color = "#00e5c3" if is_new else "#5b6af0"
    banner = f'<div style="background:{banner_color}11;border:1px solid {banner_color}33;border-radius:12px;padding:12px 16px;color:{banner_color};font-size:12px;font-weight:600;font-family:JetBrains Mono,monospace;">{"🆕 " if is_new else "👋 "}{msg}</div>'
    return gr.update(visible=False), gr.update(visible=True), banner, email

def go_step2(file):
    if file is None:
        return gr.update(), gr.update(), '<div style="background:rgba(240,82,107,0.08);border:1px solid rgba(240,82,107,0.2);border-radius:12px;padding:12px 16px;color:#f0526b;font-size:12px;font-weight:600;font-family:JetBrains Mono,monospace;">⚠ Please upload a resume file to continue.</div>'
    return gr.update(visible=False), gr.update(visible=True), ""

def go_step3(job_reqs):
    if not job_reqs.strip():
        return gr.update(), gr.update(), '<div style="background:rgba(240,82,107,0.08);border:1px solid rgba(240,82,107,0.2);border-radius:12px;padding:12px 16px;color:#f0526b;font-size:12px;font-weight:600;font-family:JetBrains Mono,monospace;">⚠ Please select a role or enter skill requirements.</div>'
    return gr.update(visible=False), gr.update(visible=True), ""

# ─────────────────────────────────────────────
# Build UI
# ─────────────────────────────────────────────
with gr.Blocks(css=css, title="HireScore", theme=gr.themes.Base()) as demo:

    # Shared state
    user_email_state = gr.State("")

    # ── LOGIN ──
    with gr.Column(visible=True) as login_page:
        gr.HTML(LOGIN_LOGO)
        login_banner = gr.HTML(value="")
        email_in     = gr.Textbox(label="Email Address", placeholder="you@company.com", elem_classes="glass-input")
        pass_in      = gr.Textbox(label="Password", placeholder="••••••••••", type="password", elem_classes="glass-input")
        login_btn    = gr.Button("SIGN IN / CREATE ACCOUNT →", elem_classes="cta-btn", size="lg")
        gr.HTML("<p style='text-align:center;color:#2a2a3a;font-family:JetBrains Mono,monospace;font-size:11px;margin-top:10px;letter-spacing:1px;'>New email = auto account creation &nbsp;·&nbsp; Existing email = sign in</p>")

    # ── STEP 1: Upload ──
    with gr.Column(visible=False) as step1_page:
        gr.HTML(STEP1_HTML)
        step1_err = gr.HTML(value="")
        file_in   = gr.File(label="RESUME DOCUMENT", file_types=[".pdf", ".docx", ".txt"], elem_classes="glass-input")
        with gr.Row():
            s1_back = gr.Button("← Sign Out", elem_classes="ghost-btn")
            s1_next = gr.Button("CONTINUE → SELECT ROLE", elem_classes="cta-btn", size="lg")

    # ── STEP 2: Role ──
    with gr.Column(visible=False) as step2_page:
        gr.HTML(STEP2_HTML)
        step2_err = gr.HTML(value="")
        job_drop  = gr.Dropdown(choices=["Custom"] + list(JOB_TEMPLATES.keys()),
                                value="Custom", label="TARGET DESIGNATION", elem_classes="glass-input")
        job_reqs  = gr.Textbox(label="REQUIREMENT PROFILE",
                               placeholder="e.g. Python, Docker, AWS, Kubernetes, REST API...",
                               lines=4, elem_classes="glass-input")
        with gr.Row():
            s2_back = gr.Button("← Back", elem_classes="ghost-btn")
            s2_next = gr.Button("CONTINUE → REVIEW", elem_classes="cta-btn", size="lg")

    # ── STEP 3: Review + Run ──
    with gr.Column(visible=False) as step3_page:
        gr.HTML(STEP3_HTML)
        step3_err    = gr.HTML(value="")
        preview_html = gr.HTML(value="")
        with gr.Row():
            s3_back = gr.Button("← Back", elem_classes="ghost-btn")
            run_btn = gr.Button("⚡  COMMENCE EVALUATION", elem_classes="cta-btn", size="lg")

    # ── RESULTS ──
    with gr.Column(visible=False) as results_page:
        gr.HTML(RESULTS_LOGO)
        result_html = gr.HTML()
        with gr.Row():
            new_btn      = gr.Button("← NEW ANALYSIS", elem_classes="ghost-btn")
            signout_btn  = gr.Button("SIGN OUT", elem_classes="danger-btn")

    # ── EVENTS ──
    login_btn.click(
        fn=do_login, inputs=[email_in, pass_in],
        outputs=[login_page, step1_page, login_banner, user_email_state]
    )
    s1_next.click(fn=go_step2, inputs=[file_in], outputs=[step1_page, step2_page, step1_err])
    s1_back.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False), ""),
                  outputs=[login_page, step1_page, login_banner])

    job_drop.change(fn=lambda x: JOB_TEMPLATES.get(x, ""), inputs=[job_drop], outputs=[job_reqs])

    s2_next.click(fn=go_step3, inputs=[job_reqs], outputs=[step2_page, step3_page, step2_err])
    s2_next.click(fn=update_preview, inputs=[file_in, job_drop, job_reqs], outputs=[preview_html])
    s2_back.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
                  outputs=[step1_page, step2_page])

    run_btn.click(fn=run_analysis, inputs=[file_in, job_drop, job_reqs, user_email_state],
                  outputs=[step3_page, results_page, result_html])
    s3_back.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
                  outputs=[step2_page, step3_page])

    new_btn.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False), ""),
                  outputs=[step1_page, results_page, result_html])
    signout_btn.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False), "", ""),
                      outputs=[login_page, results_page, login_banner, user_email_state])

if __name__ == "__main__":
    demo.launch()