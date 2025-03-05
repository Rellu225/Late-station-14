import os
import requests
import yaml
import re
from datetime import datetime

# GitHub API setup
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY", "LateStation14/Late-station-14")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
CHANGELOG_PATH = "Resources/Changelog/LateStation.yml"  # Updated to match exact case

def get_merged_prs(since_time=None):
    """Fetch merged PRs since the last run."""
    url = f"https://api.github.com/repos/{REPO}/pulls?state=closed&sort=updated&direction=desc"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    prs = response.json()

    # Filter for merged PRs
    merged_prs = [pr for pr in prs if pr["merged_at"] is not None]
    if since_time:
        merged_prs = [pr for pr in merged_prs if pr["merged_at"] > since_time]
    return merged_prs

def parse_changelog(pr_body):
    """Parse the Changelog section from the PR body."""
    if not pr_body:
        return []

    # Find the Changelog section after :cl:
    changelog_match = re.search(r":cl:.*?(?=(?:\n\n|\Z))", pr_body, re.DOTALL)
    if not changelog_match:
        return []

    changelog_text = changelog_match.group(0)
    changes = []

    # Match lines like "- add: message", "- fix: message", etc.
    for line in changelog_text.splitlines():
        line = line.strip()
        match = re.match(r"-\s*(add|remove|tweak|fix):\s*(.+)", line, re.IGNORECASE)
        if match:
            change_type, message = match.groups()
            changes.append({
                "type": change_type.capitalize(),  # Match your YAML schema (Fix, Add, etc.)
                "message": message.strip()
            })

    return changes

def load_changelog():
    """Load the existing changelog YAML or create it if it doesn't exist."""
    if not os.path.exists(CHANGELOG_PATH):
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(CHANGELOG_PATH), exist_ok=True)
        # Create an empty changelog structure
        default_changelog = {"Entries": []}
        with open(CHANGELOG_PATH, "w") as f:
            yaml.safe_dump(default_changelog, f, default_flow_style=False, sort_keys=False)
        return default_changelog
    with open(CHANGELOG_PATH, "r") as f:
        return yaml.safe_load(f)

def save_changelog(data):
    """Save the updated changelog YAML."""
    with open(CHANGELOG_PATH, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

def get_next_id(entries):
    """Get the next available ID."""
    if not entries:
        return 1
    return max(entry["id"] for entry in entries) + 1

def main():
    # Load existing changelog (or create it)
    changelog = load_changelog()
    entries = changelog.get("Entries", [])

    # Get the latest entry time to fetch PRs since then
    last_time = max((entry["time"] for entry in entries), default=None) if entries else None

    # Fetch merged PRs
    prs = get_merged_prs(since_time=last_time)
    if not prs:
        print("No new merged PRs found.")
        return

    next_id = get_next_id(entries)

    # Process each PR
    for pr in prs:
        changes = parse_changelog(pr["body"])
        if not changes:
            print(f"Skipping PR #{pr['number']}: No valid changelog found.")
            continue

        entry = {
            "id": next_id,
            "author": pr["user"]["login"],
            "time": pr["merged_at"],  # ISO format with UTC
            "url": pr["html_url"],
            "changes": changes
        }
        entries.append(entry)
        next_id += 1
        print(f"Added entry for PR #{pr['number']} by {pr['user']['login']}")

    # Update changelog
    changelog["Entries"] = entries
    save_changelog(changelog)
    print(f"Updated changelog with {len(prs)} new entries.")

if __name__ == "__main__":
    main()
