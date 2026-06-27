<div align="center">

# Google Workspace Bulk User Provisioning

<img src="https://readme-typing-svg.demolab.com?font=Inter&weight=700&size=24&duration=2800&pause=700&color=0EA5E9&center=true&vCenter=true&width=900&lines=Streamlit+Admin+Provisioning+Tool;CSV+Bulk+Upload+%2B+Admin+SDK;Secure+Google+Workspace+Automation" alt="Typing SVG" />

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/Google_Admin_SDK-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Admin SDK" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT" />
</p>

</div>

---

## Project Showcase

**Google Workspace Bulk User Provisioning** is a secure Python Streamlit application for generating and provisioning Google Workspace users using **official methods only**: CSV bulk upload and Admin SDK Directory API. Built for admins who need to create hundreds of users without manual one-by-one entry.

Designed by **Muhammad Afzal Kalwar** for enterprise Google Workspace onboarding workflows.

## Live Preview

| | |
|---|---|
| **Repository** | [github.com/mafzalkalwardev/google-workspace-bulk-user-provisioning](https://github.com/mafzalkalwardev/google-workspace-bulk-user-provisioning) |
| **Run locally** | `streamlit run app.py` |

## Screenshots

| Dashboard | Mobile |
|---|---|
| ![Dashboard](./docs/screenshots/homepage.png) | ![Mobile](./docs/screenshots/mobile.png) |

## Key Features

- Streamlit UI with password masking and security notes
- Generate 300+ users with Faker British-style names
- Unique username formats (firstname.lastname, initials, numbered)
- Fixed or random strong passwords
- Export Google Admin bulk upload CSV
- Optional Admin SDK `users.insert` provisioning
- Rate-limit retries and provisioning reports
- **No** Selenium login automation or 2SV bypass (by design)

## Tech Stack

- Python 3.10+, Streamlit, Faker, Google Admin SDK
- Pandas for CSV export

## Quick Start

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

## Project Structure

```
.
├── app.py
├── requirements.txt
├── .env.example
├── services/google_admin.py
├── utils/generate_users.py
└── exports/          # gitignored — generated CSVs
```

## Security

- Never commit `.env`, service account JSON, or `exports/*.csv`
- Use domain-wide delegation only with super-admin approval
- Rotate temporary passwords after first login

---

## About the Developer

**Muhammad Afzal Kalwar** — Full-Stack Developer & Automation Engineer  
GitHub: [@mafzalkalwardev](https://github.com/mafzalkalwardev) · Portfolio: [mafzalkalwardev.github.io](https://mafzalkalwardev.github.io)

<details>
<summary>SEO Keywords</summary>

Muhammad Afzal Kalwar, mafzalkalwardev, Google Workspace bulk user creation, Admin SDK Python, Streamlit admin tool, CSV user provisioning, automation engineer Pakistan

</details>

---

<div align="center">
  <sub>Built by Muhammad Afzal Kalwar · FT Solutions</sub>
</div>
