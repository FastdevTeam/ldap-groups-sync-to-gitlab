# ldap-groups-sync-to-gitlab

This script can help you to manage your staff between [UCS](https://www.univention.com/) and [GitLab-CE](https://about.gitlab.com/install/)

The main purpose of this script is to keep the groups and users in the GitLab up to date in accordance with LDAP

we use [Vault](https://www.vaultproject.io/) to encrypt credentials, but feel free to use any other config file or remote system to store data

# Preparations:
1. pip install -r requirements.txt
2. if you aren't using Vault:<br>
    2.1. change the value<br>
    2.2. Key "ucs_search_query" - just a query string in format "https://{HOST}/univention/udm/groups/group/{your search property}"<br>
    2.3. Key "admins" - those guys who should be ignored by the script, just a string in the format - "user1,user2,user3"<br>

# How To Run:
1. just run "python3 main.py --help" to see all available commands