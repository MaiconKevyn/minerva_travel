"""Run one durable Minerva guide job.

Invoke this process repeatedly from the queue supervisor, cron runner, or a
long-running worker wrapper. One-job execution keeps shutdown and deploy
recovery deterministic.
"""

from minerva_travel.jobs import run_once

if __name__ == "__main__":
    result = run_once()
    print(f"job_id={result.job_id or '-'} outcome={result.outcome}")
