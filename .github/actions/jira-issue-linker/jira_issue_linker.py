import re
import os
import requests
from github import Github

def extract_jira_issues(text):
    issues = re.findall(r'SCRUM-\d+', text)
    print(f"Debug: Extracted issues: {issues}")
    return issues

def get_jira_issue_info(issue):
    url = f"{os.environ['JIRA_BASE_URL']}/rest/api/3/issue/{issue}"
    auth = (os.environ['JIRA_USER_EMAIL'], os.environ['JIRA_API_TOKEN'])
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        data = response.json()
        title = data['fields']['summary']
        print(f"Debug: Retrieved title for {issue}: {title}")
        return title
    except requests.exceptions.RequestException as e:
        print(f"Error fetching info for {issue}: {str(e)}")
        return None

def create_jira_section(issues):
    if not issues:
        return ""
    section = "Jira issues linked:\n\n"
    for issue in issues:
        title = get_jira_issue_info(issue)
        if title:
            section += f"* [{issue}]({os.environ['JIRA_BASE_URL']}/browse/{issue}) {title}\n"
        else:
            section += f"* {issue} N/A\n"
    return section.strip()

def update_pr_body(original_body, new_jira_section):
    body_without_jira = re.sub(r'Jira issues linked:\n\n.*?\n---\n', '', original_body, flags=re.DOTALL)
    delimiter = "\n---\n"
    return f"{new_jira_section}{delimiter}{body_without_jira}".strip()

def main():
    g = Github(os.environ['GITHUB_TOKEN'])
    repo = g.get_repo(os.environ['REPO'])
    pr = repo.get_pull(int(os.environ['PR_NUMBER']))

    issues = set()
    issues.update(extract_jira_issues(pr.title))
    issues.update(extract_jira_issues(pr.head.ref))
    for commit in pr.get_commits():
        issues.update(extract_jira_issues(commit.commit.message))

    sorted_issues = sorted(issues, key=lambda x: int(x.split('-')[1]))

    print(f"Debug: Extracted issues: {sorted_issues}")

    new_title = re.sub(r'\s*SCRUM-\d+', '', pr.title)
    new_title += ' ' + ' '.join(sorted_issues)

    print(f"Debug: New PR title: {new_title}")

    new_jira_section = create_jira_section(sorted_issues)
    new_body = update_pr_body(pr.body or "", new_jira_section)

    print(f"Debug: New Jira section:\n{new_jira_section}")

    try:
        pr.edit(title=new_title, body=new_body)
        print("Debug: Successfully updated PR")
    except Exception as e:
        print(f"Error updating PR: {str(e)}")

if __name__ == "__main__":
    main()
