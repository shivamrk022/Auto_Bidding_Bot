# schedule_runner.py — Runs bots on a schedule without n8n
# Usage: python schedule_runner.py
import schedule, time, subprocess, sys

def run_bot():
    print("[Scheduler] Triggering bot run...")
    subprocess.run([sys.executable, "main.py", "--platform", "both"], cwd=".")

for day in ["monday","tuesday","wednesday","thursday","friday"]:
    getattr(schedule.every(), day).at("09:00").do(run_bot)
    getattr(schedule.every(), day).at("12:00").do(run_bot)
    getattr(schedule.every(), day).at("15:00").do(run_bot)

print("Scheduler running. Press Ctrl+C to stop.")
while True:
    schedule.run_pending()
    time.sleep(30)
