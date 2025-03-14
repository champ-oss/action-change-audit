"""Provides functionality to interact with GitHub."""

from datetime import datetime
from typing import Any
from github import Github, UnknownObjectException, RateLimitExceededException
import csv
import concurrent.futures
import os
import time

# Set your GitHub repository details
GITHUB_REPO = os.environ.get('GITHUB_REPO')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
TARGET_DIRECTORY = os.environ.get('TARGET_DIRECTORY')
WORKING_DIRECTORY = os.environ.get('WORKING_DIRECTORY')
REPORT_FILE = os.environ.get('REPORT_FILE', 'report.csv')
START_DATE = os.environ.get('START_DATE')  # Format: YYYY-MM-DD
END_DATE = os.environ.get('END_DATE')  # Format: YYYY-MM-DD

# Initialize GitHub API client
g = Github(GITHUB_TOKEN, per_page=100)  # Use higher page size for efficiency
repo = g.get_repo(GITHUB_REPO)


def handle_rate_limit():
    """Handles GitHub rate limits by waiting and retrying."""
    while True:
        rate_limit = g.get_rate_limit().core
        if rate_limit.remaining > 0:
            return
        reset_time = (rate_limit.reset - datetime.utcnow()).total_seconds()
        print(f"Rate limit exceeded! Sleeping for {int(reset_time)} seconds...")
        time.sleep(reset_time + 1)  # Sleep until reset


def get_merge_commits(starting_date: Any, ending_date: Any) -> list:
    """Fetch merge commits within the given date range that modified files in TARGET_DIRECTORY."""
    print("Fetching merge commits...")

    try:
        commits = [
            commit for commit in repo.get_commits(since=starting_date, until=ending_date)
            if len(commit.commit.parents) > 1  # Only merge commits
        ]
    except RateLimitExceededException:
        handle_rate_limit()
        return get_merge_commits(starting_date, ending_date)

    filtered_commits = []
    for commit in commits:
        if check_commit_changes(commit):
            filtered_commits.append(commit)

    print(f"Filtered {len(filtered_commits)} merge commits that modified {TARGET_DIRECTORY}.")
    return filtered_commits


def check_commit_changes(commit: Any) -> Any:
    """Check if a commit modified files in the TARGET_DIRECTORY. Also include *.tf files in WORKING_DIRECTORY."""
    try:
        return commit if any(
            f.filename.startswith(f"{WORKING_DIRECTORY}/{TARGET_DIRECTORY}") or f.filename.endswith(".tf")
            for f in commit.files
        ) else None
    except UnknownObjectException:
        return None  # Handle edge cases where commit data is missing


def find_prs_for_commits(merge_commits: list) -> dict:
    """Find PRs for merge commits efficiently, handling rate limits."""
    print("Fetching PRs for merge commits...")

    try:
        merged_prs = {pr.merge_commit_sha: pr for pr in
                      repo.get_pulls(state="closed", sort="updated", direction="desc")}
        return {commit.sha: merged_prs.get(commit.sha) for commit in merge_commits}
    except RateLimitExceededException:
        handle_rate_limit()
        return find_prs_for_commits(merge_commits)


def get_pr_approval_status(pr: Any) -> bool:
    """Check if a pull request was approved."""
    try:
        return any(review.state == "APPROVED" for review in pr.get_reviews())
    except RateLimitExceededException:
        handle_rate_limit()
        return get_pr_approval_status(pr)


def process_commits(merge_commits: list) -> tuple:
    """Process commits concurrently and categorize PRs into approved and unapproved."""
    pr_data = find_prs_for_commits(merge_commits)
    unapproved_prs = []
    approved_prs = []

    def check_commit(commit):
        pr = pr_data.get(commit.sha)
        if pr:
            if get_pr_approval_status(pr):
                approved_prs.append(pr.number)
            else:
                unapproved_prs.append(pr.number)
                print(f"WARNING: PR #{pr.number} modified production files but was NOT approved!")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(check_commit, merge_commits)

    return unapproved_prs, approved_prs


def generate_report(unapproved_prs: list, approved_prs: list) -> None:
    """Generate a detailed CSV report with PR links for approved and unapproved PRs."""
    total_merged = len(unapproved_prs) + len(approved_prs)

    with open(REPORT_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)

        # Report header
        writer.writerow(["GitHub Repository", GITHUB_REPO])
        writer.writerow(["Target Directory", TARGET_DIRECTORY])
        writer.writerow(["Start Date", START_DATE])
        writer.writerow(["End Date", END_DATE])
        writer.writerow([])

        # Summary Section
        writer.writerow(["Summary"])
        writer.writerow(["Total Merged PRs", total_merged])
        writer.writerow(["Total Unapproved PRs", len(unapproved_prs)])
        writer.writerow(["Total Approved PRs", len(approved_prs)])
        writer.writerow([])

        # Detailed Unapproved PR Section
        writer.writerow(["Unapproved PRs"])
        writer.writerow(["PR Number", "PR Link"])  # Column Headers
        for pr in unapproved_prs:
            pr_link = f"https://github.com/{GITHUB_REPO}/pull/{pr}"
            writer.writerow([pr, pr_link])  # Each PR with a link

        # Detailed Approved PR Section
        writer.writerow([])
        writer.writerow(["Approved PRs"])
        writer.writerow(["PR Number", "PR Link"])  # Column Headers
        for pr in approved_prs:
            pr_link = f"https://github.com/{GITHUB_REPO}/pull/{pr}"
            writer.writerow([pr, pr_link])

    print(f"Detailed Report saved as {REPORT_FILE}")


def main(starting_date: Any, ending_date: Any) -> None:
    print(f"Fetching merge commits from {starting_date} to {ending_date} affecting {TARGET_DIRECTORY}...")

    merge_commits = get_merge_commits(starting_date, ending_date)
    unapproved_prs, approved_prs = process_commits(merge_commits)

    generate_report(unapproved_prs, approved_prs)


if __name__ == "__main__":
    start_date = datetime.strptime(START_DATE, "%Y-%m-%d")
    end_date = datetime.strptime(END_DATE, "%Y-%m-%d")
    main(start_date, end_date)
