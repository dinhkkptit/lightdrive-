# 🗂️ LightDrive — Flask File Manager

A simple, self-hosted **Flask-based file manager** for your local or remote server —  
think of it as a lightweight Google Drive you can run anywhere.

---

## ✨ Features

✅ **File & Folder Management**
- Upload single or multiple files  
- Upload folders (preserves structure)  
- Drag & drop uploads with progress bar  
- Browse directories with breadcrumb navigation  
- Download files or folders (ZIP / TAR formats)  
- Delete files or folders  
- Live search filter  
- View file metadata (size, modified date)

✅ **User Accounts & Permissions**
- Built-in login system (Flask-Login + SQLite)  
- Roles:
  - **Admin** → everything (add users, delete)
  - **Editor** → upload / edit only
  - **Viewer** → read-only  
- First user automatically becomes admin

✅ **Built-in Text Editor**
- Edit text/code files directly in the browser  
- Syntax-safe textarea (UTF-8, 2 MB limit)

✅ **Responsive Dark UI**
- Lightweight, clean, keyboard-friendly  
- Works locally or on small servers / containers

---

## 🧰 Tech Stack

- **Python 3.9+**
- **Flask** + **Flask-Login**
- **SQLite** (no external DB required)
- HTML, CSS, JavaScript

---

## 🚀 Quick Start

```bash
# Clone this repository
git clone https://github.com/YOURUSERNAME/lightdrive.git
cd lightdrive

# Create environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install flask flask-login werkzeug

# Run the app
python app.py
```

## ⚙️ Environment Variables (optional)

|Variable|Default|Description|
|---|---|---|
|`FILE_ROOT`|`./storage`|Base directory for browsing/uploads|
|`FILEMGR_DB`|`./users.db`|Path to SQLite database|
|`SECRET_KEY`|`dev-secret-change-me`|Flask secret key|
|`PORT`|`5000`|Web server port|

```
Example:

`export FILE_ROOT="/mnt/data" export PORT=8080 python app.py`

---

## 🧩 Folder Structure

`lightdrive/ │ ├── app.py ├── users.db            # auto-created ├── storage/            # your files live here └── templates/     ├── base.html     ├── browse.html     ├── login.html     ├── users.html     ├── editor.html     └── error.html`

---

## 🔒 Permissions

|Role|Browse|Upload/Edit|Delete|Manage Users|
|---|---|---|---|---|
|**Viewer**|✅|❌|❌|❌|
|**Editor**|✅|✅|❌|❌|
|**Admin**|✅|✅|✅|✅|

---

## 🧠 Tips

- Use `web.archive`, `pythonanywhere`, or any VPS to host privately.
    
- Always keep the app within a **sandboxed `ROOT_DIR`**.
    
- To reset users: delete `users.db` and restart.
    

---

## 🪄 Development / Customization

- Templates use Jinja2 and simple Tailwind-like CSS.
    
- You can edit UI easily in `base.html` or add new endpoints.
    
- To add features, use the **C.R.A.F.T. Prompt** below.
    

---

## 🧩 Reuse Prompt (for ChatGPT)

If you want to update or expand this project using ChatGPT,  
keep the **CRAFT_PROMPT.txt** (below) handy for future context.

`Using my CRAFT Flask file browser context, update my Flask app to include: [your feature here].`

Example:

> “Using my CRAFT Flask file browser context, add syntax highlighting in the text editor.”

---

## 🧑‍💻 License

MIT License — free for personal or commercial use.  
Just keep attribution if you fork or publish derivatives.

**LightDrive** — lightweight. local. yours.

---

## ⚙️ `CRAFT_PROMPT.txt`

```text
### 🧩 C.R.A.F.T. Prompt

**C — Context**  
I’m building a simple Flask-based local file manager website that allows me to upload, download, browse, and manage files or folders on my host. It should support both files and folders, show folder structure, file metadata, and be user-friendly like a lightweight Google Drive.

**R — Request**  
Help me create, update, or debug a Flask app (`app.py` + `browse.html` + other templates) that provides:

1. File/folder upload (manual and drag & drop)
2. File/folder browsing with breadcrumbs
3. File download (as file, ZIP, or TAR)
4. Delete functionality
5. File size and last-modified timestamps
6. Live search filtering
7. Pretty, responsive interface (HTML/CSS/JS)
8. Account creation and permission-based login (admin/editor/viewer)
9. Online text editor directly on the site

**A — Action**  
When I ask to “update,” give me a **fully working and ready-to-run** code version (not snippets), combining backend (`app.py`) and frontend (`browse.html`, etc.).  
Ensure:

- URLs always use `/`, not `\`  
- Uploads preserve folder structure  
- Downloads work for both files and folders  
- Browsing dynamically reflects filesystem  
- Only authorized users can modify/delete files

**F — Format**  
- Complete, copy-pasteable code blocks (Python + HTML/JS)  
- Short explanations of changes  
- Optional UI improvements when requested

**T — Tone**  
Developer-friendly, clear, practical.  
Focus on real usability and stability.

---

### ✅ Example Usage

> “Using my CRAFT Flask file browser context, add password protection and dark theme.”  
> “Update it to support TAR and ZIP folder downloads side by side.”  
> “Make drag-and-drop show a progress bar.”  
> “Add syntax highlighting to the file editor.”
