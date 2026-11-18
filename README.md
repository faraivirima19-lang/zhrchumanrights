# ZHRCHumanRightsBot — Web Chat (Prototype)

A human rights information chatbot for the Zimbabwe Human Rights Commission (ZHRC).
Built with Flask + web chat interface. Supports English, Shona, and Ndebele.

## Run locally
```
pip install -r requirements.txt
python app.py
```
Open: http://localhost:5001/test

## Features
- Human rights information (Chapter 4 - Bill of Rights)
- How to file a complaint
- ZHRC services overview
- Office locations
- Emergency contacts
- Downloadable guides
- FAQ
- Multi-language (English/Shona/Ndebele)

## Deploy to Render
Push to GitHub, connect to Render. Set BASE_URL env var.

## Connect to WhatsApp (optional)
Use Meta WhatsApp Cloud API or Chatwoot. Update webhook URL to point to your Render URL.
