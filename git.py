import os
import gitlab
import logging
import gitlab.exceptions
from univention import acs
from prettytable import PrettyTable


def git_groups_list(git):
    groups = git.groups.list(all=True, order_by='name')
    git_group_list = []

    for group_id in groups:
        members = group_id.members.all(all=True)
        tmp = []
        for member_id in members:
            tmp.append(member_id.username)
        git_group_list.append({"group": str(group_id.name), "users": tmp})
    if not os.path.exists("fake_db"):
        os.makedirs("fake_db")
    with open("fake_db/git_origin.txt", "w") as data:
        data.write(str(git_group_list))
    return git_group_list, groups


def root_migration(git_auth):
    """
    Add a root account to all GitLab groups by default
    Arguments:
        git_auth - get a gitlab object after auth
    """

    groups = git_auth.groups.list(all=True, order_by='name')
    root = git_auth.users.list(search='root')
    if not root:
        logging.warning(" i can't find root!")  # here need to send message to slack
    else:
        for group in groups:
            try:
                group.members.get(root[0].id)
            except gitlab.exceptions.GitlabGetError:
                logging.info("root user [id: {}] was added to group - {}".format(root[0].id, group))
                group.members.create({'user_id': root[0].id,
                                      'access_level': gitlab.OWNER_ACCESS})


def rename_groups(git_item, ldap_item):
    if str(ldap_item['group']).capitalize() == git_item.name.capitalize():
        git_item.name = ldap_item['group']
        git_item.save()


def add_users(ldap_item, git_item, git_auth):
    if str(ldap_item['group']).capitalize() == git_item.name.capitalize():
        for ldap_user in ldap_item['users']:
            try:
                git_user = git_auth.users.list(username=ldap_user)[0]
                git_item.members.create({'user_id': git_user.id,
                                         "access_level": gitlab.DEVELOPER_ACCESS})
            except gitlab.exceptions.GitlabCreateError:
                logging.debug("User {} already exists in Gitlab, nothing to do".format(ldap_user))
                continue
            except IndexError:
                logging.warning("User {} doesn't exist in GitLab, can't be added to group - {}"
                                .format(ldap_user, str(git_item.name)))
                continue


def ldap_git_migration(ldap, git, git_auth):
    """
        Add users to identical groups and rename the groups in accordance with the LDAP
    """

    for ldap_item in ldap:
        for git_item in git:
            rename_groups(git_item, ldap_item)
            add_users(ldap_item, git_item, git_auth)


def add_internal_users(ldap_item, group, git_auth):
    for ldap_user in ldap_item['users']:
        try:
            git_user = git_auth.users.list(username=ldap_user)[0]
            group.members.create({'user_id': git_user.id,
                                  "access_level": gitlab.DEVELOPER_ACCESS})
        except IndexError:
            logging.warning("User {} doesn't exist in GitLab, can't be added to group - {}"
                            .format(ldap_user, str(group.name)))
            continue
        except gitlab.exceptions.GitlabCreateError:
            logging.debug("User {} already exists in Gitlab, nothing to do".format(ldap_user))
            continue


def internal_group(ldap, git, git_auth):
    git_groups = git_auth.groups.list(all=True, order_by='name')
    for ldap_item in ldap:
        for group in git_groups:
            if 'Internal' in ldap_item['group'].capitalize() and \
                    group.name == ldap_item['group'].split('Internal')[1]:
                add_internal_users(ldap_item, group, git_auth)


def remove_members(group, ldap_item, local):
    """
    For each ldap_item(group) check the users in Git, if user doesn't exist, just delete it
    """
    members = group.members.all(all=True)
    for member in members:
        if member.username not in ldap_item["users"] and member.username not in acs()['admins'].split(','):
            try:
                group.members.delete(member.id)
            except gitlab.exceptions.GitlabDeleteError:
                if local:
                    logging.info("for subgroup {}, user {} is linked from the root group, check it manually"
                                 .format(ldap_item['group'].split('Internal')[1], member.username))
                    continue


def git_ldap_validation(ldap, git_auth):
    """
    removes users from GitLab groups which are not present in LDAP
    Calling remove_members function
    """
    git_groups = git_auth.groups.list(all=True, order_by='name')
    for ldap_item in ldap:
        for group in git_groups:
            if 'Internal' in ldap_item['group'] and \
                    group.name == ldap_item['group'].split('Internal')[1]:
                remove_members(group, ldap_item, "local")
            if group.name.capitalize() == ldap_item['group'].capitalize():
                remove_members(group, ldap_item, None)


def enumerate_users(ldap_item, git_item):
    ldap_item["users"].sort()
    git_item["users"].sort()
    ldap_tmp = []
    git_tmp = []
    for user in ldap_item["users"]:
        if user not in git_item["users"]:
            ldap_tmp.append(user)
    for user in git_item["users"]:
        if user not in ldap_item["users"] and user not in acs()['admins'].split(','):
            git_tmp.append(user)
    return ldap_tmp, git_tmp


def dif_groups(ldap, git):
    table = PrettyTable(['Id', 'Gitlab_Group', 'Gitlab_Users'], title="These groups don't exist in LDAP")
    count = 0
    l = [str(i['group']).capitalize() for i in ldap]
    for id, i in enumerate(l):
        if 'Internal' in i:
            l[id] = i.split('Internal')[1].capitalize()
    dif = [i for i in git if not i['group'].capitalize() in l]
    for i in dif:
        count += 1
        table.add_row([count, i['group'], i['users']])
    with open("fake_db/diff_group.txt", "w") as f:
        f.write(table.get_string())
    logging.info("\n" + str(table))


def file_writer(file, table):
    with open("fake_db/" + file, "w") as f:
        f.write(table.get_string())


def enum_local_eq_groups(ldap, git, table):
    for ldap_item in ldap:
        for git_item in git:
            if 'Internal' in ldap_item['group'] and git_item["group"] == ldap_item['group'].split('Internal')[1]:
                ldap_item["users"].sort()
                git_item["users"].sort()
                if ldap_item["users"] != git_item["users"]:
                    table.add_row([ldap_item['group'].split('Internal')[1], git_item["group"], ldap_item['users'],
                                   git_item['users']])
                break


def enumerate_equal_groups(ldap, git, table):
    for ldap_item in ldap:
        for git_item in git:
            ldap_item["users"].sort()
            git_item["users"].sort()
            if ldap_item["group"] == git_item["group"] or str(ldap_item["group"]).capitalize() == git_item[
                "group"].capitalize():
                if ldap_item["users"] != git_item["users"]:
                    table.add_row([ldap_item["group"], git_item["group"], ldap_item['users'], git_item['users']])
                    break
                elif ldap_item["users"] == git_item["users"]:
                    table.add_row([ldap_item["group"], git_item["group"], "equal", "equal"])
                else:
                    table.add_row([ldap_item["group"], git_item["group"], ldap_item['users'], git_item['users']])
                break


def enumerate_migration_local_groups(ldap, git, table):
    for ldap_item in ldap:
        for git_item in git:
            if 'Internal' in ldap_item['group']:
                if git_item["group"] == ldap_item['group'].split('Internal')[1]:
                    users = enumerate_users(ldap_item, git_item)
                    table.add_row([ldap_item['group'].split('Internal')[1],
                                   users[0], users[1]])
                    break
                if git_item["group"].capitalize() == ldap_item['group'].split('Internal')[1].capitalize():
                    users = enumerate_users(ldap_item, git_item)
                    table.add_row([git_item["group"] + " -> " + ldap_item['group'].split('Internal')[1],
                                   users[0], users[1]])


def enumerate_migration_groups(ldap, git, table):
    for ldap_item in ldap:
        for git_item in git:
            try:
                if ldap_item["group"] == git_item["group"]:
                    users = enumerate_users(ldap_item, git_item)
                    table.add_row([ldap_item["group"], users[0], users[1]])
                elif str(ldap_item["group"]).capitalize() == git_item["group"].capitalize():
                    users = enumerate_users(ldap_item, git_item)
                    table.add_row(
                        [git_item["group"] + " -> " + str(ldap_item["group"]), users[0], users[1]])
            except TypeError:
                logging.warning("TypeError")
                continue
    return table


def migration_result(ldap, git):
    table = PrettyTable(["LDAP -> Git", "Users to be added to Git group (if exists in git)", "Users to be removed from "
                                                                                             "Git group"],
                        title="Result after migration")
    enumerate_migration_local_groups(ldap, git, table)
    enumerate_migration_groups(ldap, git, table)
    file_writer('migration_result.txt', table)
    logging.info("\n" + str(table))


def equal_groups(ldap, git):
    table = PrettyTable(["LDAP_Group", "GitLab_Group", "LDAP_Users", "Gitlab_Users"],
                        title="Difference between existing groups")
    enum_local_eq_groups(ldap, git, table)
    enumerate_equal_groups(ldap, git, table)
    file_writer('equal_group.txt', table)
    logging.info("\n" + str(table))


def commits_result(git):
    table = PrettyTable(['Id', 'Project', 'Project_link', 'Last commit'],
                        title="Last commit for each project in GitLab")
    projects = git.projects.list(all=True)
    tmp = []
    count = 0
    for project in projects:
        commits = project.commits.list()
        for commit in commits:
            tmp.append([str(project.name)[0:], project.web_url, str(commit.committed_date).split('T')[0][0:]])
            break
    result = sorted(tmp, key=lambda commit: commit[2])
    result.reverse()
    for res in result:
        count += 1
        table.add_row([count, res[0], res[1], res[2]])

    file_writer('last_commits.txt', table)
    logging.info("\n" + str(table))
