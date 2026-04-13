import json
import os
import sqlite3
import threading
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from speaker import speak

class JobAlertMonitor:
    def __init__(self, config_path="job_alert_config.json"):
        self.config = self._load_config(config_path)
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "job_notification.db")
        self.running = False
        self.monitor_thread = None
        self.user_skills = self._extract_user_skills()
        self._init_database()
        
    def _extract_user_skills(self) -> Dict:
        """Extract skills from CV/profile"""
        profile = self.config.get("user_profile", {})
        return {
            "tech_stack": profile.get("tech_stack", []),
            "experience_years": profile.get("experience_years", 0),
            "current_role": profile.get("current_role", "")
        }
    
    def _load_config(self, config_path):
        """Load job alert configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ Job alert config not found. Creating default...")
            default_config = self._create_default_config()
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
    
    def _create_default_config(self):
        """Create default configuration"""
        return {
            "api_provider": "theirstack",
            "api_key": "",
            "user_profile": {
                "name": "Piyush",
                "current_role": "MERN-Stack Developer",
                "experience_years": 1,
                "tech_stack": ["MERN", "React", "Node.js", "Express", "MongoDB"],
                "location": "India",
                "remote_preference": "remote"
            },
            "search_criteria": {
                "keywords": ["MERN", "React", "Node.js", "Full Stack"],
                "job_titles": ["MERN Stack Developer", "Full Stack Developer"],
                "locations": ["Remote", "India"],
                "remote_only": True,
                "job_types": ["full-time"],
                "experience_level": ["entry", "junior", "mid"]
            },
            "notification_settings": {
                "check_interval_minutes": 60,
                "max_jobs_per_notification": 5,
                "min_match_score": 40,
                "channels": ["speak", "desktop_notification"]
            }
        }
    
    def _init_database(self):
        """Initialize SQLite database for seen jobs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    job_id TEXT PRIMARY KEY,
                    title TEXT,
                    company TEXT,
                    url TEXT,
                    match_score INTEGER,
                    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notified BOOLEAN DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS job_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_title TEXT,
                    company TEXT,
                    match_score INTEGER,
                    notified_at TIMESTAMP
                )
            ''')
    
    def calculate_match_score(self, job: Dict) -> int:
        """
        Calculate how well a job matches Piyush's CV/profile
        Score range: 0-100
        """
        score = 0
        criteria = self.config["search_criteria"]
        user_skills = self.user_skills["tech_stack"]
        
        # 1. Title match (30 points max)
        title = job.get('title', '').lower()
        title_keywords = ['mern', 'full stack', 'react', 'node', 'mean', 'javascript']
        for keyword in title_keywords:
            if keyword in title:
                score += 6  # 5 keywords * 6 = 30 max
        
        # 2. Skills match (40 points max)
        job_description = job.get('description', '').lower()
        job_title_desc = f"{title} {job_description}"
        
        # Core skills (must-have)
        core_skills = criteria.get("must_have_skills", ["React", "Node.js", "MongoDB"])
        for skill in core_skills:
            if skill.lower() in job_title_desc:
                score += 10  # 3 core skills * 10 = 30
        
        # Nice-to-have skills
        nice_skills = criteria.get("nice_to_have_skills", ["Next.js", "React Native", "TypeScript"])
        for skill in nice_skills:
            if skill.lower() in job_title_desc:
                score += 3  # Extra bonus
        
        # 3. Company preference (15 points max)
        preferred_companies = criteria.get("preferred_companies", [])
        company = job.get('company', '').lower()
        for pref in preferred_companies:
            if pref.lower() in company:
                score += 15
                break
        
        # 4. Experience level (10 points)
        exp_level = criteria.get("experience_level", ["entry", "junior", "mid"])
        job_exp = job.get('experience_level', 'mid').lower()
        if job_exp in exp_level:
            score += 10
        
        # 5. Location/Remote (5 points)
        if criteria.get("remote_only", False) and job.get('is_remote', False):
            score += 5
        elif 'remote' in job_title_desc or 'work from home' in job_title_desc:
            score += 5
        
        return min(score, 100)
    
    def search_jobs(self) -> List[Dict]:
        """Search for jobs using TheirStack API or fallback to web scraping"""
        
        # Method 1: TheirStack API (Recommended)
        if self.config.get("api_key"):
            return self._search_via_theirstack()
        
        # Method 2: Free alternative - Web scraping job boards
        else:
            print("⚠️ No API key found. Using web scraping fallback...")
            return self._search_via_scraping()
    
    def _search_via_theirstack(self) -> List[Dict]:
        """Search using TheirStack API"""
        api_key = self.config.get("api_key", "")
        
        # If no API key, use web scraping
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            print("⚠️ No API key configured. Using web scraping...")
            return self._search_via_scraping()
        
        criteria = self.config["search_criteria"]
        
        url = "https://api.theirstack.com/v1/jobs/search"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Build search query - simplified to avoid 422 error
        keywords = criteria.get("keywords", ["MERN", "React", "Node.js"])
        keywords_str = " OR ".join(keywords)
        
        payload = {
            "query": keywords_str,
            "limit": 20
        }
        
        # Add optional filters only if they exist
        if criteria.get("job_types"):
            payload["job_type"] = criteria["job_types"]
        if criteria.get("remote_only"):
            payload["remote_only"] = True
        
        try:
            print(f"🔍 Searching for jobs with keywords: {keywords_str[:50]}...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                jobs = self._parse_jobs(data.get("data", []))
                print(f"✅ Found {len(jobs)} jobs from API")
                return jobs
            else:
                print(f"⚠️ API error {response.status_code}: {response.text[:100]}")
                print("🔄 Falling back to web scraping...")
                return self._search_via_scraping()
                
        except Exception as e:
            print(f"❌ API request failed: {e}")
            print("🔄 Falling back to web scraping...")
            return self._search_via_scraping()
    
    def _search_via_scraping(self) -> List[Dict]:
        """Free fallback: scrape job boards"""
        jobs = []
        
        print("🔍 Using web scraping to find jobs...")
        
        # Indeed.com (best for Indian market)
        indeed_jobs = self._scrape_indeed()
        jobs.extend(indeed_jobs)
        print(f"   Indeed: {len(indeed_jobs)} jobs")
        
        # RemoteOK (great for remote tech jobs)
        remote_jobs = self._scrape_remoteok()
        jobs.extend(remote_jobs)
        print(f"   RemoteOK: {len(remote_jobs)} jobs")
        
        # We Work Remotely
        wwr_jobs = self._scrape_weworkremotely()
        jobs.extend(wwr_jobs)
        print(f"   WeWorkRemotely: {len(wwr_jobs)} jobs")
        
        # Remove duplicates by URL
        unique_jobs = []
        seen_urls = set()
        for job in jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        
        print(f"📊 Total unique jobs found: {len(unique_jobs)}")
        return unique_jobs
    
    def _scrape_indeed(self) -> List[Dict]:
        """Scrape Indeed for MERN jobs in India"""
        try:
            from bs4 import BeautifulSoup
            
            # Search for MERN jobs in India
            keywords = "MERN+stack+developer+India"
            url = f"https://www.indeed.co.in/jobs?q={keywords}&remote=1"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            jobs = []
            for job_card in soup.find_all('div', class_='job_seen_beacon')[:15]:
                title_elem = job_card.find('h2', class_='jobTitle')
                company_elem = job_card.find('span', class_='companyName')
                location_elem = job_card.find('div', class_='companyLocation')
                
                if title_elem and company_elem:
                    title = title_elem.text.strip()
                    company = company_elem.text.strip()
                    location = location_elem.text.strip() if location_elem else "Remote"
                    
                    # Check if relevant to MERN
                    if any(skill in title.lower() for skill in ['mern', 'react', 'node', 'full stack']):
                        jobs.append({
                            'id': f"indeed_{hash(title + company)}",
                            'title': title,
                            'company': company,
                            'location': location,
                            'url': f"https://www.indeed.co.in{job_card.find('a')['href']}" if job_card.find('a') else "#",
                            'source': 'Indeed',
                            'is_remote': 'remote' in location.lower() or 'work from home' in location.lower()
                        })
            return jobs
        except Exception as e:
            print(f"⚠️ Indeed scraping error: {e}")
            return []
    
    def _scrape_linkedin(self) -> List[Dict]:
        """
        LinkedIn scraping is not supported — LinkedIn actively blocks crawlers
        and rate-limits unauthenticated requests.
        Use the official LinkedIn Jobs API or a third-party aggregator instead.
        """
        print("ℹ️  LinkedIn scraping skipped (not supported without API access)")
        return []
    
    def _scrape_remoteok(self) -> List[Dict]:
        """Scrape RemoteOK for remote MERN jobs"""
        try:
            from bs4 import BeautifulSoup
            
            url = "https://remoteok.com/remote-react-jobs"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            jobs = []
            for job in soup.find_all('tr', class_='job')[:15]:
                title_elem = job.find('h2')
                company_elem = job.find('h3')
                
                if title_elem:
                    title = title_elem.text.strip()
                    # Check if relevant
                    if any(skill in title.lower() for skill in ['react', 'node', 'mern', 'full stack']):
                        jobs.append({
                            'id': f"remoteok_{hash(title)}",
                            'title': title,
                            'company': company_elem.text.strip() if company_elem else "Unknown",
                            'location': "Remote",
                            'url': f"https://remoteok.com{job.find('a')['href']}" if job.find('a') else "#",
                            'source': 'RemoteOK',
                            'is_remote': True
                        })
            return jobs
        except Exception as e:
            print(f"⚠️ RemoteOK scraping error: {e}")
            return []
    
    def _scrape_weworkremotely(self) -> List[Dict]:
        """Scrape We Work Remotely"""
        try:
            from bs4 import BeautifulSoup
            
            url = "https://weworkremotely.com/categories/remote-programming-jobs"
            response = requests.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            jobs = []
            for job in soup.find_all('li', class_='feature')[:15]:
                title_elem = job.find('span', class_='title')
                company_elem = job.find('span', class_='company')
                
                if title_elem:
                    title = title_elem.text.strip()
                    if any(skill in title.lower() for skill in ['react', 'node', 'javascript', 'full stack']):
                        jobs.append({
                            'id': f"wwr_{hash(title)}",
                            'title': title,
                            'company': company_elem.text.strip() if company_elem else "Unknown",
                            'location': "Remote",
                            'url': f"https://weworkremotely.com{job.find('a')['href']}" if job.find('a') else "#",
                            'source': 'WeWorkRemotely',
                            'is_remote': True
                        })
            return jobs
        except Exception as e:
            print(f"⚠️ WeWorkRemotely scraping error: {e}")
            return []
    
    def _parse_jobs(self, raw_jobs: List[Dict]) -> List[Dict]:
        """Parse and normalize job data from API"""
        parsed = []
        for job in raw_jobs:
            parsed.append({
                'id': job.get('id', f"job_{hash(job.get('title', ''))}"),
                'title': job.get('title', 'Unknown'),
                'company': job.get('company', {}).get('name', 'Unknown'),
                'location': job.get('location', 'Remote'),
                'url': job.get('url', '#'),
                'source': job.get('source', 'API'),
                'posted_at': job.get('posted_at', datetime.now().isoformat()),
                'description': job.get('description', '')[:500],
                'is_remote': job.get('is_remote', True),
                'experience_level': job.get('experience_level', 'junior')
            })
        return parsed
    
    def get_new_jobs(self) -> List[Dict]:
        """Get only jobs that haven't been seen before"""
        all_jobs = self.search_jobs()
        new_jobs = []
        min_score = self.config["notification_settings"].get("min_match_score", 40)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for job in all_jobs:
                # Calculate match score based on CV
                job['match_score'] = self.calculate_match_score(job)
                
                # Skip low-quality matches
                if job['match_score'] < min_score:
                    continue
                
                # Check if job already seen
                cursor.execute(
                    "SELECT notified, match_score FROM seen_jobs WHERE job_id = ?",
                    (job['id'],)
                )
                result = cursor.fetchone()
                
                if not result:
                    # New job
                    new_jobs.append(job)
                    cursor.execute(
                        """INSERT INTO seen_jobs (job_id, title, company, url, match_score) 
                           VALUES (?, ?, ?, ?, ?)""",
                        (job['id'], job['title'], job['company'], job['url'], job['match_score'])
                    )
                elif result[0] == 0:
                    # Job exists but not notified yet
                    new_jobs.append(job)
            
            conn.commit()
        
        # Sort by match score (highest first)
        new_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        return new_jobs
    
    def notify_jobs(self, jobs: List[Dict]):
        """Send personalized notifications for new jobs"""
        if not jobs:
            return
        
        max_jobs = self.config["notification_settings"]["max_jobs_per_notification"]
        jobs_to_notify = jobs[:max_jobs]
        
        # Find the best match
        best_match = jobs_to_notify[0] if jobs_to_notify else None
        
        # Speak personalized notification
        speak(f"Good news Piyush! I found {len(jobs_to_notify)} new MERN stack jobs matching your profile")
        time.sleep(1.5)
        
        if best_match and best_match.get('match_score', 0) >= 70:
            speak(f"Top match: {best_match['title']} at {best_match['company']}")
            speak(f"This job matches {best_match['match_score']} percent of your skills")
            time.sleep(1)
        
        for i, job in enumerate(jobs_to_notify[:3], 1):
            speak(f"Job {i}: {job['title']} at {job['company']}")
            if job.get('match_score', 0) > 0:
                speak(f"Match score: {job['match_score']} percent")
            time.sleep(0.8)
        
        if len(jobs_to_notify) > 3:
            speak(f"And {len(jobs_to_notify) - 3} more jobs")
        
        speak("Say 'show jobs' to see all matches, or 'apply' to open the links")
        
        # Desktop notifications
        if "desktop_notification" in self.config["notification_settings"]["channels"]:
            self._send_desktop_notifications(jobs_to_notify)
        
        # Store in database for later reference
        with sqlite3.connect(self.db_path) as conn:
            for job in jobs_to_notify:
                conn.execute(
                    "INSERT OR REPLACE INTO job_alerts (job_title, company, match_score, notified_at) VALUES (?, ?, ?, ?)",
                    (job['title'], job['company'], job['match_score'], datetime.now().isoformat())
                )
                conn.execute(
                    "UPDATE seen_jobs SET notified = 1 WHERE job_id = ?",
                    (job['id'],)
                )
            conn.commit()
    
    def _send_desktop_notifications(self, jobs: List[Dict]):
        """Send Windows desktop notifications"""
        try:
            from plyer import notification
            for job in jobs[:3]:
                notification.notify(
                    title=f"🎯 New Job: {job['company']}",
                    message=f"{job['title']}\nMatch: {job.get('match_score', 0)}%\nClick to view",
                    timeout=5,
                    app_name="Reminder Bot"
                )
        except ImportError:
            print("⚠️ plyer not installed. Skipping desktop notifications.")
        except Exception as e:
            print(f"⚠️ Desktop notification failed: {e}")
    
    def get_top_matches(self, limit: int = 10) -> List[Dict]:
        """Get top job matches from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT job_title, company, match_score, notified_at 
                   FROM job_alerts 
                   ORDER BY match_score DESC, notified_at DESC 
                   LIMIT ?""",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def start_monitoring(self):
        """Start the job monitoring thread"""
        if self.running:
            print("⚠️ Job monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        speak("Job alert monitor activated. I'll notify you when I find matching positions.")
        print("✅ Job alert monitor started")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        check_interval = self.config["notification_settings"]["check_interval_minutes"]
        
        # Do first check immediately
        self._check_and_notify()
        
        while self.running:
            try:
                # Sleep in small increments to allow stopping
                for _ in range(check_interval * 60):
                    if not self.running:
                        break
                    time.sleep(1)
                
                if self.running:
                    self._check_and_notify()
                    
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                time.sleep(60)
    
    def _check_and_notify(self):
        """Check for jobs and notify if found"""
        # Check quiet hours
        if self._is_quiet_hours():
            print("🔕 Quiet hours active. Skipping notification.")
            return
        
        print(f"\n🔍 Checking for new MERN jobs... ({datetime.now().strftime('%H:%M:%S')})")
        new_jobs = self.get_new_jobs()
        
        if new_jobs:
            print(f"📢 Found {len(new_jobs)} new jobs matching your profile!")
            self.notify_jobs(new_jobs)
        else:
            print("✅ No new matching jobs found")
    
    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        quiet = self.config["notification_settings"].get("quiet_hours", {})
        if not quiet.get("enabled", False):
            return False
        
        now = datetime.now().time()
        start = datetime.strptime(quiet["start"], "%H:%M").time()
        end = datetime.strptime(quiet["end"], "%H:%M").time()
        
        if start < end:
            return start <= now < end
        else:
            return now >= start or now < end
    
    def stop_monitoring(self):
        """Stop the job monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("✅ Job alert monitor stopped")
    
    def check_now(self) -> List[Dict]:
        """Manual check for jobs (for clap command)"""
        print("\n🔍 Manual job check initiated...")
        speak("Checking for new jobs now")
        
        new_jobs = self.get_new_jobs()
        
        if new_jobs:
            print(f"📢 Found {len(new_jobs)} new jobs!")
            self.notify_jobs(new_jobs)
            return new_jobs
        else:
            print("✅ No new jobs found")
            speak("No new MERN stack jobs found at this time")
            return []
    
    def show_saved_jobs(self):
        """Show previously saved job matches"""
        jobs = self.get_top_matches(10)
        if jobs:
            speak(f"You have {len(jobs)} saved job matches")
            for i, job in enumerate(jobs[:5], 1):
                speak(f"{i}. {job['job_title']} at {job['company']} - {job['match_score']} percent match")
        else:
            speak("No saved job matches yet")

# Standalone test
if __name__ == "__main__":
    monitor = JobAlertMonitor()
    monitor.check_now()