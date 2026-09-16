# Neo.Rex: Intelligent ATS Co-Pilot & Application Automation Engine

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Chrome Extension](https://img.shields.io/badge/Manifest-V3-orange.svg)](https://developer.chrome.com/docs/extensions/mv3/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Author](https://img.shields.io/badge/Author-Vineeth%20Yadav-blue.svg)](https://github.com/vineethyadav110)


An intelligent, privacy-first job application co-pilot designed to streamline candidate workflows across modern Applicant Tracking Systems (ATS). Features an autonomous DOM-injection browser extension, a high-precision job role evaluator, an AI-powered screening question engine, and a multi-step Workday post-login assistant.

---

## 📌 Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [1. Backend Setup](#1-backend-setup)
  - [2. Chrome Extension Setup](#2-chrome-extension-setup)
- [Platform Support](#platform-support)
- [Configuration & Customization](#configuration--customization)
- [API Reference](#api-reference)
- [Security & Ethical Automation](#security--ethical-automation)
- [License](#license)

---

## 💡 Overview

Modern job seekers face hours of repetitive data entry across fragmented ATS portals (Workday, Greenhouse, Lever, Ashby), often answering identical compliance, compensation, and technical screening questions. 

**Neo.Rex** solves this with a **human-in-the-loop co-pilot model**:
1. **Evaluates Job Descriptions:** Analyzes requirements against candidate competencies with a 200+ taxonomy scoring algorithm and clustered equivalence credit.
2. **Generates Tailored Materials:** Dynamically crafts targeted cover letters in `.docx` format.
3. **Automates Repetitive DOM Interactions:** Intelligently maps and populates inputs, comboboxes, and file upload fields via native browser event dispatching.
4. **Navigates Complex Multi-Step Portals:** Solves Workday multi-step post-login wizards by scanning `data-automation-id` attributes and filling only unpopulated fields.
5. **Answers Dynamic Screening Questions:** Utilizes a hybrid rules-and-context engine with local caching to answer legal, demographic, compensation, and open-ended technical questions.

---

## ✨ Key Features

### 1. Workday Post-Login Multi-Step Co-Pilot
* **Context-Aware DOM Traversal:** Targets Workday's React-rendered forms using `data-automation-id` attributes and ARIA roles.
* **Non-Destructive Empty-Box Scanner:** Scans and populates only empty fields, preserving pre-filled profile information.
* **React State Bridge:** Dispatches input and change events directly using prototype property descriptors (`Object.getOwnPropertyDescriptor`), ensuring underlying React forms recognize state updates.
* **Visual Verification:** Highlights automated fields in emerald green (`#10b981`) for review before clicking *Save and Continue*.

### 2. AI Screening & Dynamic Question Engine
* **Local Query Cache:** Employs an embedded SQLite key-value store to deliver instant answers for previously encountered questions.
* **Deterministic Rule Engine:** Accurately handles legal, visa sponsorship, work authorization, salary expectations, notice period, and location queries without external API calls.
* **STAR Framework Synthesis:** Employs structured STAR (Situation, Task, Action, Result) methodology to craft responses for open-ended technical and behavioral prompts.
* **Dropdown Option Alignment:** Automatically normalizes candidate profile metrics to portal select options (e.g., mapping "3.5 years" to `"3 - 5 years"`).

### 3. High-Precision Job Role Evaluator
* **Domain-Specific Taxonomy:** Analyzes 200+ data analytics, business intelligence, data warehousing, and software engineering competencies.
* **Clustered Equivalence:** Grants partial/cluster credit for equivalent ecosystem tools (e.g., crediting Azure Synapse experience when AWS Redshift or Snowflake is requested).
* **Noise & Boilerplate Filtering:** Filters out generic company overview copy and EEO disclaimers, isolating substantive role requirements.

### 4. Automated File Attachment via DataTransfer API
* Generates formatted Word documents (`.docx`) tailored to the specific role and company.
* Injects generated files directly into portal file inputs via browser `DataTransfer` objects, bypassing manual file-picker dialogs.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         CHROME EXTENSION (MV3)                           │
│                                                                          │
│   ┌──────────────────────────┐            ┌──────────────────────────┐   │
│   │   popup.html / popup.js  │            │    content_script.js     │   │
│   │  • Job Match Scoring     │            │  • DOM Scraper & Mapper  │   │
│   │  • Cover Letter Preview  │            │  • React Event Dispatcher│   │
│   │  • One-Click Autofill    │            │  • Workday Floating Bar  │   │
│   └─────────────┬────────────┘            └─────────────┬────────────┘   │
└─────────────────┼───────────────────────────────────────┼────────────────┘
                  │               HTTP / REST             │
                  └───────────────────┬───────────────────┘
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND                                │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │                      API ROUTING & ENDPOINTS                     │   │
│   │   POST /api/evaluate  •  POST /api/autofill  •  POST /api/review │   │
│   │   POST /api/screening/answer  •  GET /api/documents/cover-letter│   │
│   └─────────────────────────────────┬────────────────────────────────┘   │
│                                     │                                    │
│       ┌─────────────────────────────┼─────────────────────────────┐      │
│       ▼                             ▼                             ▼      │
│ ┌───────────────┐           ┌───────────────┐             ┌────────────┐ │
│ │  EVALUATOR    │           │   SCREENING   │             │  ADAPTERS  │ │
│ │ • 200+ Taxon  │           │ • Rules Layer │             │ • Workday  │ │
│ │ • Equivalence │           │ • SQLite Cache│             │ • Greenh.  │ │
│ │ • Core Weight │           │ • STAR Synthes│             │ • Lever    │ │
│ └───────┬───────┘           └───────┬───────┘             │ • Ashby    │ │
│         │                           │                     └─────┬──────┘ │
│         └───────────────────────────┼───────────────────────────┘        │
│                                     ▼                                    │
│                    ┌─────────────────────────────────┐                   │
│                    │     PERSISTENCE & TRACKING      │                   │
│                    │  • SQLite Application DB        │                   │
│                    │  • JSON Backup & Sync           │                   │
│                    │  • .docx Document Generator     │                   │
│                    └─────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

* **Backend:** Python 3.9+, FastAPI, Uvicorn, Pydantic v2
* **Document Processing:** python-docx
* **Storage:** SQLite3, JSON sync backup
* **Frontend / Extension:** Chrome Extension Manifest V3, Vanilla JavaScript (ES6+), Modern DOM Mutation Observers, Custom CSS3
* **Testing:** Python unittest, FastAPI TestClient

---

## 📁 Project Structure

```
neorex-automation-engine/
├── setup.sh                       # One-command automated setup script
├── start_server.sh                # Server launcher script
├── stop_server.sh                 # Process cleanup script
├── requirements.txt               # Python package dependencies
├── README.md                      # Project documentation
├── .gitignore                     # Git tracking exclusions
└── neorex/
    ├── adapters/                  # ATS-specific form & field adapters
    │   ├── base.py                # Abstract portal adapter interface
    │   ├── greenhouse.py          # Greenhouse adapter implementation
    │   ├── lever.py               # Lever adapter implementation
    │   ├── ashby.py               # Ashby adapter implementation
    │   ├── generic.py             # Generic & Workday wizard adapter
    │   └── registry.py            # Adapter factory and resolver
    ├── api/
    │   └── server.py              # FastAPI application & endpoints
    ├── core/
    │   ├── models.py              # Pydantic data schemas
    │   ├── evaluator.py           # Job description evaluator & scoring engine
    │   ├── mapper.py              # Form field mapper & AI screening engine
    │   ├── review_layer.py        # Human-in-the-loop review enforcement
    │   └── storage.py             # SQLite tracking & JSON persistence
    ├── data/                      # Local database & generated artifacts
    ├── extension/                 # Chrome Manifest V3 extension
    │   ├── manifest.json          # Extension manifest & permissions
    │   ├── popup.html             # Co-pilot popup UI
    │   ├── popup.js               # Extension controller logic
    │   └── content_script.js      # In-page DOM inspector & autofill agent
    └── tests/
        └── test_system.py         # End-to-end integration test suite
```

---

## 🚀 Quick Start

### Prerequisites
* **Python 3.9+** installed on your system.
* **Google Chrome** (or any Chromium-based browser such as Brave or Edge).

### 1. Backend Setup

Clone the repository and run the automated setup script:

```bash
git clone https://github.com/vineethyadav110/neorex-automation-engine.git
cd neorex-automation-engine

# Run the automated installer
./setup.sh
```

The script automatically prepares a local virtual environment, installs dependencies, initializes databases, and performs verification checks.

Next, start the server:

```bash
./start_server.sh
```
The server will start listening at `http://127.0.0.1:8000`. You can review the API documentation at `http://127.0.0.1:8000/docs`.

### 2. Chrome Extension Setup

1. Open Chrome and navigate to `chrome://extensions`.
2. Toggle on **Developer mode** in the top-right corner.
3. Click **Load unpacked** in the top-left corner.
4. Select the `neorex/extension` folder inside the project directory.
5. Pin the **Neo.Rex** icon to your Chrome toolbar.

---

## 🌐 Platform Support

| ATS Portal | Supported Workflow | Automated Capabilities |
| :--- | :--- | :--- |
| **Workday** (`*.myworkdayjobs.com`) | Multi-Step Post-Login Wizard | • Scans empty `data-automation-id` fields<br>• Solves dynamic screening textareas<br>• Dispatches React state events<br>• Visual emerald verification |
| **Greenhouse** (`boards.greenhouse.io`) | Single-page Application | • Contact & profile autofill<br>• Custom dropdown matching<br>• Direct cover letter auto-attachment |
| **Lever** (`jobs.lever.co`) | Single-page Application | • Core profile mapping<br>• Dynamic question resolution<br>• Attachment file dispatch |
| **Ashby** (`jobs.ashbyhq.com`) | Dynamic Component Form | • Shadow DOM & reactive input updates<br>• Document upload injection |

---

## ⚙️ Configuration & Customization

To tailor Neo.Rex to your own background:

1. **Candidate Profile:** Open `neorex/core/mapper.py` to update candidate profile information (name, contact details, LinkedIn, GitHub, portfolio).
2. **Deterministic Rules:** Customize standard screening answers (work authorization, notice period, location preferences) in `neorex/core/mapper.py` under `JobApplicationStrategy`.
3. **Domain Taxonomy:** Extend target keywords, frameworks, and tools in `neorex/core/evaluator.py`.

---

## 📡 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/evaluate` | Evaluates a job description against candidate competencies and returns score breakdown. |
| `POST` | `/api/autofill` | Generates candidate autofill payload for detected portal. |
| `POST` | `/api/screening/answer` | Answers a screening question using rules, cache, or STAR synthesis. |
| `POST` | `/api/review` | Creates a human-in-the-loop review record. |
| `POST` | `/api/submit` | Records final application submission outcome. |
| `GET` | `/api/documents/cover-letter` | Generates and downloads tailored `.docx` cover letter. |
| `GET` | `/api/applications` | Lists application history from SQLite tracking database. |

---

## 🛡️ Security & Ethical Automation

* **Local-First Architecture:** All candidate personal data, application logs, and database records remain strictly on your local machine (`127.0.0.1`).
* **Human-in-the-Loop Policy:** Neo.Rex does not perform blind background submissions. All autofilled fields are visibly highlighted on screen, leaving final review and submission control in your hands.
* **Credentials Safety:** Neo.Rex never asks for, records, or stores login passwords for any portal. Users log into corporate portals independently before invoking the co-pilot.

---

## 👨‍💻 Author & Maintainer

**Vineeth Yadav Kanneboina**  
*Data Analyst & Analytics Engineer*  
* **GitHub:** [@vineethyadav110](https://github.com/vineethyadav110)

If Neo.Rex helped you streamline your job search, feel free to ⭐ star the repository!

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
