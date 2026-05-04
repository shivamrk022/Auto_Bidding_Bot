# n8n Workflow Setup

## Node order:
1. Cron — every 3 hours
2. IF — check business hours
   Condition: {{ new Date().getHours() >= 9 && new Date().getHours() < 18 }}
3. Execute Command — cd /path/to/auto-bidding-bot && venv\Scripts\python main.py --platform both
4. (Optional) Send Email / Slack notification

## Cron expression: 0 9,12,15 * * 1-5
Runs at 9am, 12pm, 3pm — Monday to Friday only.
