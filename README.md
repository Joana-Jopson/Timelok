⏳ Timelok

Timelok is a smart HR & Attendance Management System built with Django.
It combines AI-powered face recognition, real-time chat, an intelligent HR chatbot, and role-based access control into one unified platform.

The goal of Timelok is simple:
👉 Make attendance seamless, communication transparent, and HR data smarter.

✨ Features

-> Face Recognition Attendance
Secure and accurate punch-in/out using OpenCV + FaceNet.

-> Smart Chat System
   Managers and employees can chat, share files, and collaborate. Messages are automatically checked for inappropriate language.

-> AI Chatbot Assistant
   Powered by spaCy + Transformers, it understands natural questions like:
   “What time did I punch in yesterday?”
   “Do I have leave next week?”
   “Who was late today?”

-> Role & Privilege Management
   Fine-grained access to modules/submodules with scopes (OWN, NODE, ALL).

-> Dashboards & Analytics
   Attendance summaries, latecomer detection, trends, and anomaly reports.

-> Holiday & Calendar Management
   Organization-wide holidays + per-employee punch calendar views.


⚙️ Installation

1. Clone the repository
<pre> ``` git clone https://github.com/<yourusername>/Timelok.git
cd Timelok
   ``` </pre>

2. Create a virtual environment
<pre> ``` python -m venv venv
source venv/bin/activate    # On Mac/Linux
venv\Scripts\activate       # On Windows  ``` </pre>

3. Install dependencies
All requirements are listed in requirements.txt.

4. Database Setup
Timelok uses SQL Server with mssql-django and pyodbc.

📂 Project Notes

Media & Static
All employee photos, leave documents, and uploaded files are stored in media/ and static/.
These folders must exist before running the project.

Face Recognition
Powered by OpenCV + pytorch-facenet.
Ensure your system has a working camera (for live recognition) or proper image uploads enabled.
Make sure you have SQL Server running and update your settings.py with your DB credentials.

💡 Why Timelok?

-> HR systems are often clunky and outdated. Timelok was built to be:
-> Smart → with AI features that understand human questions.
-> Secure → face recognition + role-based access.
-> Transparent → analytics dashboards for managers and employees.
-> Human-friendly → simple design, less paperwork, more automation.

🔑 Timelok: Because time is too valuable to waste on manual HR work.
