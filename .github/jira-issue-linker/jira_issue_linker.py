import re
import os
import requests
from github import Github

def extract_jira_tickets(text):
    tickets = re.findall(r'SCRUM-\d+', text)
    print(f"Debug: Extracted tickets: {tickets}")
    return tickets

def get_jira_ticket_info(ticket):
    url = f"{os.environ['JIRA_BASE_URL']}/rest/api/3/issue/{ticket}"
    auth = (os.environ['JIRA_USER_EMAIL'], os.environ['JIRA_API_TOKEN'])
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        data = response.json()
        title = data['fields']['summary']
        print(f"Debug: Retrieved title for {ticket}: {title}")
        return title
    except requests.exceptions.RequestException as e:
        print(f"Error fetching info for {ticket}: {str(e)}")
        return None

def create_jira_section(tickets):
    if not tickets:
        return ""
    section = "Jira issues linked:\n\n"
    for ticket in tickets:
        title = get_jira_ticket_info(ticket)
        if title:
            section += f"* [{ticket}]({os.environ['JIRA_BASE_URL']}/browse/{ticket}) {title}\n"
        else:
            section += f"* {ticket} N/A\n"
    return section.strip()

def update_pr_body(original_body, new_jira_section):
    body_without_jira = re.sub(r'Jira issues linked:\n\n.*?\n---\n', '', original_body, flags=re.DOTALL)
    delimiter = "\n---\n"
    return f"{new_jira_section}{delimiter}{body_without_jira}".strip()

def main():
    g = Github(os.environ['GITHUB_TOKEN'])
    repo = g.get_repo(os.environ['REPO'])
    pr = repo.get_pull(int(os.environ['PR_NUMBER']))

    tickets = set()
    tickets.update(extract_jira_tickets(pr.title))
    tickets.update(extract_jira_tickets(pr.head.ref))
    for commit in pr.get_commits():
        tickets.update(extract_jira_tickets(commit.commit.message))

    sorted_tickets = sorted(tickets, key=lambda x: int(x.split('-')[1]))

    print(f"Debug: Extracted tickets: {sorted_tickets}")

    new_title = re.sub(r'\s*SCRUM-\d+', '', pr.title)
    new_title += ' ' + ' '.join(sorted_tickets)

    print(f"Debug: New PR title: {new_title}")

    new_jira_section = create_jira_section(sorted_tickets)
    new_body = update_pr_body(pr.body or "", new_jira_section)

    print(f"Debug: New Jira section:\n{new_jira_section}")

    try:
        pr.edit(title=new_title, body=new_body)
        print("Debug: Successfully updated PR")
    except Exception as e:
        print(f"Error updating PR: {str(e)}")

if __name__ == "__main__":
    main()
