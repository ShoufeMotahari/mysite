# Create this as management/commands/analyze_logs.py

import json
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Analyze password manager logs for security insights"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days to analyze (default: 7)",
        )
        parser.add_argument(
            "--log-type",
            choices=["security", "auth", "admin", "all"],
            default="all",
            help="Type of logs to analyze",
        )
        parser.add_argument(
            "--output-format",
            choices=["json", "text"],
            default="text",
            help="Output format",
        )
        parser.add_argument(
            "--alert-threshold",
            type=int,
            default=5,
            help="Alert threshold for failed attempts",
        )

    def handle(self, *args, **options):
        days = options["days"]
        log_type = options["log_type"]
        output_format = options["output_format"]
        alert_threshold = options["alert_threshold"]

        self.stdout.write(f"Analyzing logs for the last {days} days...")

        try:
            results = self.analyze_logs(days, log_type, alert_threshold)

            if output_format == "json":
                self.stdout.write(json.dumps(results, indent=2, default=str))
            else:
                self.print_text_report(results)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error analyzing logs: {str(e)}"))

    def analyze_logs(self, days, log_type, alert_threshold):
        """Analyze logs and return security insights"""

        logs_dir = getattr(settings, "LOGS_DIR", "logs")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        results = {
            "analysis_period": {"start": start_date, "end": end_date, "days": days},
            "security_events": defaultdict(int),
            "failed_logins": [],
            "suspicious_activities": [],
            "user_activities": defaultdict(int),
            "ip_activities": defaultdict(int),
            "password_operations": defaultdict(int),
            "admin_activities": [],
            "alerts": [],
        }

        # Log files to analyze
        log_files = []
        if log_type in ["security", "all"]:
            log_files.append(os.path.join(logs_dir, "security.log"))
        if log_type in ["auth", "all"]:
            log_files.append(os.path.join(logs_dir, "auth.log"))
        if log_type in ["admin", "all"]:
            log_files.append(os.path.join(logs_dir, "admin.log"))
        if log_type == "all":
            log_files.append(os.path.join(logs_dir, "password_manager.log"))

        # Analyze each log file
        for log_file in log_files:
            if os.path.exists(log_file):
                self.analyze_log_file(log_file, start_date, end_date, results)

        # Generate alerts
        self.generate_alerts(results, alert_threshold)

        return results

    def analyze_log_file(self, log_file, start_date, end_date, results):
        """Analyze a single log file"""

        try:
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        # Parse log entry
                        entry = self.parse_log_entry(line, start_date, end_date)
                        if not entry:
                            continue

                        # Analyze different types of events
                        self.analyze_security_events(entry, results)
                        self.analyze_user_activities(entry, results)
                        self.analyze_failed_logins(entry, results)
                        self.analyze_password_operations(entry, results)
                        self.analyze_admin_activities(entry, results)
                        self.detect_suspicious_activities(entry, results)

                    except Exception as e:
                        logger.warning(f"Error parsing log entry: {str(e)}")
                        continue

        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {str(e)}")

    def parse_log_entry(self, line, start_date, end_date):
        """Parse a log entry and extract relevant information"""

        # Regular expression to parse log entries
        log_pattern = r"\[([^\]]+)\] (\w+) ([^\s]+) ([^\s]+)\.([^\s]+):(\d+) - (.+)"
        match = re.match(log_pattern, line)

        if not match:
            return None

        timestamp_str, level, logger_name, module, function, line_num, message = (
            match.groups()
        )

        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
        except ValueError:
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None

        # Filter by date range
        if timestamp < start_date or timestamp > end_date:
            return None

        return {
            "timestamp": timestamp,
            "level": level,
            "logger": logger_name,
            "module": module,
            "function": function,
            "line": line_num,
            "message": message,
        }

    def analyze_security_events(self, entry, results):
        """Analyze security-related events"""

        message = entry["message"].lower()

        if "login failed" in message:
            results["security_events"]["failed_logins"] += 1
        elif "login successful" in message:
            results["security_events"]["successful_logins"] += 1
        elif "password encrypted" in message:
            results["security_events"]["password_encryptions"] += 1
        elif "password decrypted" in message:
            results["security_events"]["password_decryptions"] += 1
        elif "admin access" in message:
            results["security_events"]["admin_access"] += 1
        elif "permission denied" in message:
            results["security_events"]["permission_denied"] += 1
        elif "suspicious activity" in message:
            results["security_events"]["suspicious_activities"] += 1

    def analyze_user_activities(self, entry, results):
        """Analyze user activities"""

        message = entry["message"]

        # Extract username from message
        user_match = re.search(r"User: (\w+)", message)
        if user_match:
            username = user_match.group(1)
            results["user_activities"][username] += 1

        # Extract IP address from message
        ip_match = re.search(r"IP: ([\d\.]+)", message)
        if ip_match:
            ip = ip_match.group(1)
            results["ip_activities"][ip] += 1

    def analyze_failed_logins(self, entry, results):
        """Analyze failed login attempts"""

        if "login failed" in entry["message"].lower():
            # Extract details
            user_match = re.search(r"Username: (\w+)", entry["message"])
            ip_match = re.search(r"IP: ([\d\.]+)", entry["message"])

            failed_login = {
                "timestamp": entry["timestamp"],
                "username": user_match.group(1) if user_match else "Unknown",
                "ip": ip_match.group(1) if ip_match else "Unknown",
                "user_agent": "Unknown",
            }

            results["failed_logins"].append(failed_login)

    def analyze_password_operations(self, entry, results):
        """Analyze password-related operations"""

        message = entry["message"].lower()

        if "password entry added" in message:
            results["password_operations"]["added"] += 1
        elif "password entry updated" in message:
            results["password_operations"]["updated"] += 1
        elif "password entry deleted" in message:
            results["password_operations"]["deleted"] += 1
        elif "password viewed" in message:
            results["password_operations"]["viewed"] += 1

    def analyze_admin_activities(self, entry, results):
        """Analyze admin activities"""

        if "admin" in entry["message"].lower():
            admin_activity = {
                "timestamp": entry["timestamp"],
                "level": entry["level"],
                "message": entry["message"],
            }
            results["admin_activities"].append(admin_activity)

    def detect_suspicious_activities(self, entry, results):
        """Detect suspicious activities"""

        message = entry["message"].lower()

        # Multiple failed logins
        if "login failed" in message:
            ip_match = re.search(r"IP: ([\d\.]+)", entry["message"])
            if ip_match:
                ip = ip_match.group(1)
                # Check for multiple failures from same IP
                recent_failures = [
                    f
                    for f in results["failed_logins"]
                    if f["ip"] == ip
                    and (entry["timestamp"] - f["timestamp"]).total_seconds()
                    < 300  # 5 minutes
                ]

                if len(recent_failures) >= 3:
                    results["suspicious_activities"].append(
                        {
                            "type": "multiple_failed_logins",
                            "ip": ip,
                            "count": len(recent_failures),
                            "timestamp": entry["timestamp"],
                        }
                    )

        # Unusual access patterns
        if "admin access" in message and entry["timestamp"].hour < 6:
            results["suspicious_activities"].append(
                {
                    "type": "off_hours_admin_access",
                    "timestamp": entry["timestamp"],
                    "message": entry["message"],
                }
            )

        # Rapid password operations
        if "password" in message and ("added" in message or "updated" in message):
            # Check for rapid operations
            user_match = re.search(r"User: (\w+)", entry["message"])
            if user_match:
                username = user_match.group(1)
                recent_ops = [
                    entry["timestamp"]
                    for entry in results.get("recent_password_ops", [])
                    if entry.get("user") == username
                    and (entry["timestamp"] - entry["timestamp"]).total_seconds() < 60
                ]

                if len(recent_ops) >= 5:
                    results["suspicious_activities"].append(
                        {
                            "type": "rapid_password_operations",
                            "user": username,
                            "count": len(recent_ops),
                            "timestamp": entry["timestamp"],
                        }
                    )

    def generate_alerts(self, results, alert_threshold):
        """Generate security alerts based on analysis"""

        alerts = []

        # Alert for multiple failed logins
        ip_failures = defaultdict(int)
        for failure in results["failed_logins"]:
            ip_failures[failure["ip"]] += 1

        for ip, count in ip_failures.items():
            if count >= alert_threshold:
                alerts.append(
                    {
                        "type": "CRITICAL",
                        "message": f"Multiple failed login attempts from IP {ip}: {count} attempts",
                        "ip": ip,
                        "count": count,
                    }
                )

        # Alert for suspicious activities
        if results["suspicious_activities"]:
            alerts.append(
                {
                    "type": "WARNING",
                    "message": f"Detected {len(results['suspicious_activities'])} suspicious activities",
                    "count": len(results["suspicious_activities"]),
                }
            )

        # Alert for off-hours admin access
        off_hours_admin = [
            activity
            for activity in results["admin_activities"]
            if activity["timestamp"].hour < 6 or activity["timestamp"].hour > 22
        ]

        if off_hours_admin:
            alerts.append(
                {
                    "type": "WARNING",
                    "message": f"Off-hours admin access detected: {len(off_hours_admin)} instances",
                    "count": len(off_hours_admin),
                }
            )

        # Alert for high password operation volume
        total_ops = sum(results["password_operations"].values())
        if total_ops > 100:  # Threshold for high volume
            alerts.append(
                {
                    "type": "INFO",
                    "message": f"High password operation volume: {total_ops} operations",
                    "count": total_ops,
                }
            )

        results["alerts"] = alerts

    def print_text_report(self, results):
        """Print analysis results in text format"""

        self.stdout.write(
            self.style.SUCCESS("\n=== PASSWORD MANAGER LOG ANALYSIS REPORT ===\n")
        )

        # Analysis period
        period = results["analysis_period"]
        self.stdout.write(
            f"Analysis Period: {period['start'].strftime('%Y-%m-%d %H:%M:%S')} to {period['end'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.stdout.write(f"Duration: {period['days']} days\n")

        # Security events summary
        self.stdout.write(self.style.SUCCESS("SECURITY EVENTS SUMMARY:"))
        for event, count in results["security_events"].items():
            self.stdout.write(f"  {event.replace('_', ' ').title()}: {count}")
        self.stdout.write("")

        # Password operations summary
        self.stdout.write(self.style.SUCCESS("PASSWORD OPERATIONS SUMMARY:"))
        for operation, count in results["password_operations"].items():
            self.stdout.write(f"  {operation.capitalize()}: {count}")
        self.stdout.write("")

        # Top users by activity
        self.stdout.write(self.style.SUCCESS("TOP USERS BY ACTIVITY:"))
        top_users = Counter(results["user_activities"]).most_common(10)
        for user, count in top_users:
            self.stdout.write(f"  {user}: {count} activities")
        self.stdout.write("")

        # Top IPs by activity
        self.stdout.write(self.style.SUCCESS("TOP IPs BY ACTIVITY:"))
        top_ips = Counter(results["ip_activities"]).most_common(10)
        for ip, count in top_ips:
            self.stdout.write(f"  {ip}: {count} activities")
        self.stdout.write("")

        # Failed logins
        if results["failed_logins"]:
            self.stdout.write(self.style.WARNING("FAILED LOGIN ATTEMPTS:"))
            for failure in results["failed_logins"][-10:]:  # Show last 10
                self.stdout.write(
                    f"  {failure['timestamp']} - User: {failure['username']}, IP: {failure['ip']}"
                )
            self.stdout.write("")

        # Suspicious activities
        if results["suspicious_activities"]:
            self.stdout.write(self.style.WARNING("SUSPICIOUS ACTIVITIES:"))
            for activity in results["suspicious_activities"]:
                self.stdout.write(
                    f"  {activity['timestamp']} - Type: {activity['type']}"
                )
            self.stdout.write("")

        # Recent admin activities
        if results["admin_activities"]:
            self.stdout.write(self.style.SUCCESS("RECENT ADMIN ACTIVITIES:"))
            for activity in results["admin_activities"][-10:]:  # Show last 10
                self.stdout.write(f"  {activity['timestamp']} - {activity['message']}")
            self.stdout.write("")

        # Alerts
        if results["alerts"]:
            self.stdout.write(self.style.ERROR("SECURITY ALERTS:"))
            for alert in results["alerts"]:
                style = (
                    self.style.ERROR
                    if alert["type"] == "CRITICAL"
                    else self.style.WARNING
                )
                self.stdout.write(style(f"  [{alert['type']}] {alert['message']}"))
            self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("=== END OF REPORT ===\n"))


# Additional utility for real-time log monitoring
class LogMonitor:
    """Real-time log monitoring utility"""

    def __init__(self, log_file, callback):
        self.log_file = log_file
        self.callback = callback
        self.running = False

    def start_monitoring(self):
        """Start monitoring log file for new entries"""
        self.running = True

        try:
            with open(self.log_file, "r") as f:
                # Move to end of file
                f.seek(0, 2)

                while self.running:
                    line = f.readline()
                    if line:
                        self.callback(line.strip())
                    else:
                        time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error monitoring log file: {str(e)}")

    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False


# Example usage of LogMonitor
def security_alert_callback(log_entry):
    """Callback function for security alerts"""
    if any(
        keyword in log_entry.lower()
        for keyword in ["failed", "error", "warning", "suspicious"]
    ):
        logger.warning(f"Security alert: {log_entry}")
        # Send notification (email, SMS, etc.)


# Log rotation and cleanup utility
def cleanup_old_logs(logs_dir, days_to_keep=30):
    """Clean up old log files"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    for filename in os.listdir(logs_dir):
        if filename.endswith(".log"):
            filepath = os.path.join(logs_dir, filename)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

            if file_mtime < cutoff_date:
                os.remove(filepath)
                logger.info(f"Deleted old log file: {filename}")


# Performance monitoring
def monitor_log_performance():
    """Monitor log file performance and size"""
    logs_dir = getattr(settings, "LOGS_DIR", "logs")

    for filename in os.listdir(logs_dir):
        if filename.endswith(".log"):
            filepath = os.path.join(logs_dir, filename)
            file_size = os.path.getsize(filepath)

            # Alert if log file is too large (>50MB)
            if file_size > 50 * 1024 * 1024:
                logger.warning(
                    f"Large log file detected: {filename} ({file_size / 1024 / 1024:.1f} MB)"
                )
