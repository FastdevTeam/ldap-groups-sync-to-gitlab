import os
import json
import requests
from ldap3 import Server, Connection, ALL


def acs():
    if os.path.exists("creds-local.json"):
        with open("creds-local.json") as f:
            credentials = json.load(f)
    else:
        with open("creds.json") as f:
            credentials = json.load(f)
    return credentials


# There are two options to connect to UCS(LDAP) via requests module or via LDAP3

def ucs_groups_list(user, password):
    session = requests.Session()
    session.auth = (user, password)
    response = session.get(acs()['ucs_search_query'],
                           headers={"Accept": "application/json"},
                           )
    ucs_group_list = []
    raw = json.loads(response.text)

    for group in raw['_embedded']['udm:object']:
        group_name = group['dn'].split(",")[0].split("=")[1]
        tmp = []
        for users in group['properties']['users']:
            tmp.append(users.split(",")[0].split("=")[1])
        ucs_group_list.append({'group': group_name, 'users': tmp})
    if not os.path.exists("fake_db"):
        os.makedirs("fake_db")
    with open("fake_db/ucs_origin.txt", "w") as data:
        data.write(str(ucs_group_list))
    return ucs_group_list


def ldap_groups_list(user, password, ucs_host, ucs_port):
    # define the server
    s = Server(ucs_host, port=int(ucs_port),
               get_info=ALL)  # define an unsecure LDAP server, requesting info on DSE and schema

    # define the connection
    c = Connection(s, user=user,
                   password=password)
    ldap_group_list = []
    if c.bind():
        c.search(search_base='{}'.format(acs()['ldap_search_query']),
                 search_filter='(objectClass=*)',
                 attributes=['cn', 'memberUid'])
        for ldap_object in c.entries:
            tmp = []
            for users in ldap_object['memberUID']:
                tmp.append(users)
            ldap_group_list.append({'group': str(ldap_object['cn']), 'users': tmp})
    else:
        print('error in bind', c.result)
    if not os.path.exists("fake_db"):
        os.makedirs("fake_db")
    with open("fake_db/ucs_origin.txt", "w") as data:
        data.write(str(ldap_group_list))
    return ldap_group_list
