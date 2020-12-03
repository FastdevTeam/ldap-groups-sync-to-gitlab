# ldap-groups-sync-to-gitlab

This script can help you to manage your staff between [UCS](https://www.univention.com/) and [GitLab-CE](https://about.gitlab.com/install/)

The main purpose of this script is to keep the groups and users in the GitLab up to date in accordance with LDAP

we use [Vault](https://www.vaultproject.io/) to encrypt credentials, but feel free to use any other config file or remote system to store data

# Preparations:
If you aren't using Vault:
* edit the values in _creds.json_ file
* Key "ucs_search_query" - just a query string in format "https://{HOST}/univention/udm/groups/group/{your search property}"
* Key "admins" - those guys who should be ignored by the script, just a string in the format - "user1,user2,user3"

# How To Run:
## Manually:
```
pip install -r requirements.txt
```
```
python3 cli.py --help
```

## Run via Docker and Make:
- show expected result after main migration 
```
make build show_pre_migration
```
- run the main migration:
```
make all
```
- show the difference between equal LDAP - Gitlab existing groups
```
make build show_equals
```
- show groups that aren't in LDAP 
```
make build show_diff
```
- show all commits older than 3 years
```
make build show_last_commit 
```
