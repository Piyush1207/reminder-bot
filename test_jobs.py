#!/usr/bin/env python3
"""Test job alert monitoring functionality"""

from job_alert_monitor import JobAlertMonitor
import sys

print("=" * 60)
print("🔍 JOB ALERT MONITOR - FUNCTIONALITY TEST")
print("=" * 60)

# Initialize monitor
monitor = JobAlertMonitor()

print("\n📋 Config Status:")
print(f"  API Key: {'✅ Present' if monitor.config.get('api_key') and monitor.config.get('api_key') != 'YOUR_API_KEY_HERE' else '❌ Missing'}")
print(f"  User Profile: {monitor.config.get('user_profile', {}).get('name', 'Unknown')}")
print(f"  Search Keywords: {len(monitor.config.get('search_criteria', {}).get('keywords', []))} configured")

print("\n🔍 Testing Job Search...")
print("  Attempting: TheirStack API → Web Scraping fallback")

jobs = monitor.search_jobs()

print(f"\n✅ Search Complete")
print(f"📊 Results: {len(jobs)} jobs found")

if jobs:
    print(f"\n📋 Sample Results (First 3):")
    for i, job in enumerate(jobs[:3], 1):
        print(f"\n  Job {i}:")
        print(f"    Title: {job.get('title', 'N/A')}")
        print(f"    Company: {job.get('company', 'N/A')}")
        print(f"    Location: {job.get('location', 'N/A')}")
        print(f"    Remote: {'✅ Yes' if job.get('is_remote') else '❌ No'}")
        print(f"    Source: {job.get('source', 'Unknown')}")
    
    print("\n🎯 Testing Job Matching Algorithm:")
    sample_job = jobs[0]
    score = monitor.calculate_match_score(sample_job)
    print(f"  Job: {sample_job.get('title')}")
    print(f"  Match Score: {score}%")
    
    print("\n💾 Testing Database Storage:")
    new_jobs = monitor.get_new_jobs()
    print(f"  New Jobs (not yet seen): {len(new_jobs)}")
    
    if new_jobs:
        print(f"  Testing notification system...")
        monitor.notify_jobs(new_jobs[:1])
        print(f"  ✅ Notifications sent")
else:
    print("\n⚠️  No jobs found")
    print("   Possible reasons:")
    print("   1. API key is invalid or expired")
    print("   2. Web scraping selectors outdated (sites changed HTML)")
    print("   3. Rate limiting / network issues")
    print("   4. Job sites temporarily down")

print("\n📊 Database Status:")
import sqlite3
db_path = monitor.db_path
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM seen_jobs")
seen_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM job_alerts")
alert_count = cursor.fetchone()[0]
conn.close()
print(f"  Seen Jobs: {seen_count}")
print(f"  Notifications Sent: {alert_count}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
