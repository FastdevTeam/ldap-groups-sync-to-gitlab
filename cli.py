import ast
import gitlab
import os.path
import argparse
import logging
from univention import acs
from git import root_migration, ldap_git_migration, git_ldap_validation, \
    internal_group, dif_groups, equal_groups, migration_result, commits_result

logging.basicConfig(level=logging.INFO)

access = acs()


def git_auth(host, api):
    gl = gitlab.Gitlab(host, private_token=api)
    gl.auth()
    return gl


def file_reader():
    with open("fake_db/git_origin.txt") as f:
        git = ast.literal_eval(f.read())
    with open("fake_db/ucs_origin.txt") as f:
        ucs = ast.literal_eval(f.read())

    return ucs, git


def file_check():
    if not os.path.exists('fake_db/git_origin.txt') or not os.path.exists('fake_db/ucs_origin.txt'):
        from univention import ucs_groups_list
        from git import git_groups_list
        git_groups_list(git_auth(access["git_host"], access["git_api"]))[0]
        ucs_groups_list(access["ucs_user"], access["ucs_pass"])


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        "-r",
        "--run",
        action="store_const",
        const=True,
        default=False,
        help="run the main migration, ldap auth by default, if you want to change it use the '-auth' key")

    parser.add_argument(
        "-s",
        "--show",
        action="store_const",
        const=True,
        default=False,
        help="show reports, use it with '-mode' key.")

    parser.add_argument("-mode",
                        help="'diff' - show group not in ldap.\n'equal' - show difference between existing groups.\n"
                             "'mgn' - show result before migration.\n"
                             "'commit - show commits with date'\n", default='magic', required=False)
    parser.add_argument("-auth",
                        help="'ldap' - auth to UCS(LDAP) via 'ldap3' library (using by default).\n"
                             "'http' - auth to UCS(LDAP) via 'requests' library", default='ldap', required=False)
    args = parser.parse_args()

    if args.run and args.mode == "magic":
        from univention import ucs_groups_list, ldap_groups_list
        from git import git_groups_list
        if args.auth == "http":
            ldap_auth = ucs_groups_list(access["ucs_user"], access["ucs_pass"])
        else:
            ldap_auth = ldap_groups_list(access['ldap_user'], access["ldap_pass"],
                                         access["ucs_host"], access['ucs_port'])
        root_migration(git_auth(access["git_host"], access["git_api"]))
        ldap_git_migration(ldap_auth,
                           git_groups_list(git_auth(access["git_host"], access["git_api"]))[1],
                           git_auth(access["git_host"], access["git_api"]))
        internal_group(ldap_auth,
                       git_groups_list(git_auth(access["git_host"], access["git_api"]))[0],
                       git_auth(access["git_host"], access["git_api"]))
        git_ldap_validation(ldap_auth,
                            git_auth(access["git_host"], access["git_api"]))
    elif args.show and args.mode == "diff":
        file_check()
        dif_groups(file_reader()[0], file_reader()[1])
    elif args.show and args.mode == "equal":
        file_check()
        equal_groups(file_reader()[0], file_reader()[1])
    elif args.show and args.mode == "mgn":
        file_check()
        migration_result(file_reader()[0], file_reader()[1])
    elif args.show and args.mode == "commit":
        file_check()
        commits_result(git_auth(access["git_host"], access["git_api"])),
    else:
        logging.info(' freak parameters, please check it')


if __name__ == '__main__':
    main()