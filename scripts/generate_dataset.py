from pathlib import Path
import csv
import random
from datetime import datetime, timedelta

random.seed(42)
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

categories = {
    "Wi-Fi / DNS": [
        "Laptop connected to Wi-Fi but no internet access",
        "Wireless icon shows connected but websites do not load",
        "Internet unavailable although Wi-Fi is connected",
        "DNS error while connected to office Wi-Fi",
        "Wi-Fi connected but browser says no internet",
    ],
    "VPN": [
        "VPN disconnects every few minutes",
        "Remote access VPN drops after login",
        "VPN authentication fails after Windows update",
        "Company VPN connects then immediately disconnects",
        "VPN tunnel is unstable from home network",
    ],
    "Outlook / MFA": [
        "Outlook keeps asking for password",
        "MFA approval never arrives on phone",
        "Outlook cannot send email after password change",
        "Authenticator code is rejected",
        "Outlook profile fails to synchronize mail",
    ],
    "Accounts / Passwords": [
        "User account is locked after failed login attempts",
        "Cannot sign in after password reset",
        "Password expired and user cannot log in",
        "Account says credentials are invalid",
        "New employee account cannot access portal",
    ],
    "Printers": [
        "Printer is online but jobs stay in queue",
        "Office printer prints blank pages",
        "Windows cannot find network printer",
        "Print queue is stuck and cannot be cleared",
        "Printer shows offline although it is powered on",
    ],
    "Windows / Updates": [
        "Windows update failed and rolled back",
        "Laptop is slow after Windows 11 update",
        "Blue screen appears after installing an update",
        "Windows driver error after restart",
        "Computer repeatedly restarts after Windows update",
    ],
    "Software Installation": [
        "Application installation fails with permission error",
        "Software setup cannot continue because admin rights are required",
        "Installer stops before completion",
        "Approved software cannot be installed on laptop",
        "Setup wizard reports missing dependency",
    ],
    "Remote Desktop": [
        "Remote Desktop cannot connect to office PC",
        "RDP session disconnects after login",
        "Remote computer is unavailable through RDP",
        "Remote Desktop shows credential error",
        "RDP connection times out from home network",
    ],
}

priorities = ["Low", "Medium", "High"]
departments = ["Finance", "HR", "IT", "Operations", "Sales", "Academic"]
os_values = ["Windows 10", "Windows 11", "macOS", "Ubuntu"]


def noisy(text: str) -> str:
    additions = [
        "This started this morning.",
        "I already restarted the device once.",
        "It happens on my work laptop.",
        "Please help because I need this for work.",
        "The issue happens repeatedly.",
        "No recent hardware changes were made.",
    ]
    return f"{text}. {random.choice(additions)}"


def make_tickets():
    rows = []
    all_categories = list(categories.keys())
    start = datetime(2026, 1, 1)
    for i in range(1, 501):
        category = random.choice(all_categories)
        base = random.choice(categories[category])
        unknown_bsod = category == "Windows / Updates" and i % 41 == 0
        if unknown_bsod:
            base = "Laptop suddenly shows blue screen error 0x00000124"
        created = start + timedelta(days=random.randint(0, 240))
        status = "Open" if unknown_bsod else random.choice(["Resolved", "Resolved", "Resolved", "Open"])
        resolution = ""
        if status == "Resolved":
            resolution = {
                "Wi-Fi / DNS": "Restarted the network adapter and flushed the DNS cache.",
                "VPN": "Updated the VPN client and re-created the connection profile.",
                "Outlook / MFA": "Re-registered MFA and cleared cached Outlook credentials.",
                "Accounts / Passwords": "Unlocked the account and forced a secure password reset.",
                "Printers": "Cleared the print queue and reinstalled the approved printer driver.",
                "Windows / Updates": "Installed pending driver updates and repaired Windows update components.",
                "Software Installation": "Used the approved installer with administrator permission.",
                "Remote Desktop": "Enabled the approved RDP rule and verified the device was reachable.",
            }[category]
        rows.append({
            "ticket_id": f"SYN-{i:04d}",
            "created_at": created.date().isoformat(),
            "department": random.choice(departments),
            "title": base,
            "description": noisy(base + f" on {random.choice(os_values)}"),
            "resolution_notes": resolution,
            "priority": random.choice(priorities),
            "status": status,
            "pii_masked": "true",
            "ground_truth_category": category,
        })
    return rows


def article_templates():
    # Intentionally no article dedicated to BSOD error 0x00000124.
    templates = {
        "Wi-Fi / DNS": [
            ("DNS Cache Recovery", "If Wi-Fi is connected but internet access is unavailable, open Command Prompt and run ipconfig /flushdns. Reconnect to Wi-Fi and test again."),
            ("Renew Windows IP Address", "For Wi-Fi connected with no internet, run ipconfig /release followed by ipconfig /renew, then reconnect to the wireless network."),
            ("Restart Network Adapter", "Disable and re-enable the Wi-Fi network adapter, then reconnect to the approved wireless network."),
        ],
        "VPN": [
            ("VPN Client Update", "If the VPN disconnects repeatedly, update the approved VPN client to the current organization-supported version and restart the client."),
            ("Re-create VPN Profile", "Remove the damaged VPN connection profile and create a new profile using the approved organization settings."),
        ],
        "Outlook / MFA": [
            ("Re-register MFA", "If MFA approvals or codes fail, remove the old authenticator registration and complete the organization's approved MFA registration process again."),
            ("Clear Outlook Cached Credentials", "Close Outlook, remove stale Microsoft Office credentials from Windows Credential Manager, reopen Outlook, and sign in again."),
        ],
        "Accounts / Passwords": [
            ("Unlock User Account", "Verify the user's identity, unlock the account using the approved admin workflow, and ask the user to sign in again."),
            ("Password Reset Process", "Use the approved password reset portal, create a compliant password, and sign in again after the reset completes."),
        ],
        "Printers": [
            ("Clear Print Queue", "Stop the print spooler, clear stuck print jobs, restart the print spooler, and try printing again."),
            ("Reinstall Printer Driver", "Remove the existing printer and install the organization-approved printer driver before reconnecting the printer."),
        ],
        "Windows / Updates": [
            ("Repair Windows Update", "Run the Windows Update troubleshooter, restart the computer, and install pending approved updates."),
            ("Update Device Drivers", "Install manufacturer-approved device drivers through the approved update channel and restart the computer."),
        ],
        "Software Installation": [
            ("Approved Software Installation", "Download the installer only from the approved internal source and install it with authorized administrator permission."),
            ("Missing Dependency Fix", "Install the approved prerequisite package listed by the software owner, then run the installer again."),
        ],
        "Remote Desktop": [
            ("RDP Connectivity Check", "Confirm the destination computer is powered on, reachable, and allowed by the approved Remote Desktop firewall policy."),
            ("RDP Credential Repair", "Remove saved Remote Desktop credentials and reconnect using the current organization account."),
        ],
    }
    return templates


def make_kb():
    templates = article_templates()
    rows = []
    cats = list(templates.keys())
    counter = 1
    while len(rows) < 80:
        category = cats[(counter - 1) % len(cats)]
        title, body = templates[category][(counter - 1) % len(templates[category])]
        variant = (counter - 1) // len(cats) + 1
        status = "approved"
        supported_os = "Any"
        authoritative = "true"
        source_type = "Internal KB"
        if category == "VPN" and variant == 2:
            supported_os = "Windows 10"
            body = body + " This older article was written for Windows 10 and should be reviewed for newer systems."
        if category == "Printers" and variant == 3:
            body = body + " This is a near-duplicate article retained for evaluation of duplicate knowledge."
        rows.append({
            "doc_id": f"KB-{counter:03d}",
            "title": f"{title} - Guide {variant}",
            "body": body,
            "source_type": source_type,
            "authoritative": authoritative,
            "created_at": "2025-01-15",
            "updated_at": "2026-08-01" if variant % 2 else "2023-01-15",
            "status": status,
            "supported_os": supported_os,
            "security_class": "internal",
            "category": category,
        })
        counter += 1
    return rows


def write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    tickets = make_tickets()
    kb = make_kb()
    write_csv(DATA_DIR / "tickets.csv", tickets)
    write_csv(DATA_DIR / "knowledge_base.csv", kb)
    print(f"Created {len(tickets)} synthetic tickets at {DATA_DIR / 'tickets.csv'}")
    print(f"Created {len(kb)} knowledge articles at {DATA_DIR / 'knowledge_base.csv'}")
