IvhuRedu 
Integrated Digital Agriculture Extension Platform for Rural Zimbabwe

IvhuRedu is a progressive digital platform that connects smallholder farmers with Agritex extension workers through an offline-first mobile app, USSD and bulk SMS channels, and a web-based regional management dashboard. The platform strengthens agricultural extension services in rural Zimbabwe by enabling data-driven decision making even in areas with weak or no internet connectivity.
This repository contains the backend API for IvhuRedu, built with FastAPI. It handles user authentication and roles, USSD request routing, offline field report sync, bulk SMS alert dissemination, location resolution, and supervisor dashboard analytic

Key Features

User Management

Registration and authentication for three user roles: farmer, extension_worker, and district_supervisor.

USSD Request & Extension Worker Routing

Farmers dial a USSD code to request extension visits, farming advice, or report land degradation. The system uses the Haversine Formula to calculate the shortest distance between farmer and available extension worker GPS coordinates, automatically assigning the nearest available worker for rapid response. Extension workers can also submit urgent field reports via USSD for immediate supervisor attention.

Offline Field Reporting

Extension workers compile comprehensive site assessment reports (text + photographic evidence) during field visits via the offline mobile app. Reports are cached locally in SQLite when offline, and a background sync engine automatically uploads data to the central server when connectivity is restored. Incoming SMS notifications alert workers of new visit requests even without internet.

Bulk SMS Alerts

District supervisors send ward-level or district-wide SMS broadcasts for weather warnings, pest outbreaks, and climate-smart farming guidance (e.g., Pfumvudza land preparation reminders). Powered by Africa's Talking API for cross-network delivery, with delivery status tracking for each recipient.

Regional Management Dashboard
A React-based web dashboard with Leaflet interactive maps visualizes farmer registrations, field reports, land degradation incidents, and extension worker coverage. Real-time KPIs include response times, visit frequency, soil condition reports, and sustainable practice adoption rates, enabling data-driven resource allocation and policy decisions.

Location 
Addresses and location descriptions submitted by users are resolved to geographic coordinates via the LocationIQ API and stored for reuse across the system (farmer routing, ward mapping, and dashboard visualization).

The database schema consists of entities designed to support rural farming, extension services, and regional management. At its foundation the farmer, extension worker and supervisor tables store profile data for farmers, extension workers, and district supervisors, which then links to specialized tables USSD and SMS targeting. System interactions and field activities are captured via the ussd_request table, which logs farmer requests and computes routing distances, and the field_report table, which tracks offline-syncing site assessments and multimedia evidence collected during visits. location table stores the geographic location records (coordinates, formatted address) referenced by the system for the harvesine formula calculations. Finally, the communication system is managed by the sms_alert table to store bulk messages dispatched via Africa's Talking, alongside the sms_recipient junction table which audits individual delivery statuses directly on the management dashboard. 

Tech Stack

Framework:FastAPI (Python)
Database:Relational (SQL) — see data model above

External services:LocationIQ API for geocoding and address formatting, Africa's Talking for USSD and Bulk SMS

Prerequisites

Python 3.10+
A running instance of your chosen SQL database (e.g., PostgreSQL/MySQL)
API credentials for LocationIQ
pipfor dependency management
Installation
git clone git@github.com:akirachix/Nyeredzi_Backend.git
cd Nyeredzi-Backend

python -m venv venv
source env/bin/activate 

pip install -r requirements.txt

Running the App

uvicorn app.main:app --reload

The API will be available at http://localhost:8000, with interactive documentation at http://localhost:8000/docs.
Environment Variables

VariableDescriptionDATABASE_URLConnection string for the SQL databaseLOCATIONIQ_API_KEYAPI key for the LocationIQ geocoding serviceSECRET_KEYSecret key used for hashing/signing (e.g., JWT)
Project Structure

app/
├── main.py            # FastAPI app entrypoint
├── models/             # Database models 
├── schemas/             # Pydantic schemas for request/response validation
├── routers/             # API route definitions
├── services/             # Business logic (recycler assignment, geocoding, report generation)
└── core/                 # Config, security, database session management

