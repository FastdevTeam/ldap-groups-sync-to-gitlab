all: build run

build:
		docker build -t ldap-groups-sync-to-gitlab .

start: run

run:
		docker run --rm ldap-groups-sync-to-gitlab -r -mode magic

show_equals:
		docker run --rm ldap-groups-sync-to-gitlab -s -mode equal

show_diff:
		docker run --rm ldap-groups-sync-to-gitlab -s -mode diff

show_pre_migration:
		docker run --rm ldap-groups-sync-to-gitlab -s -mode mgn

show_last_commit:
		docker run --rm ldap-groups-sync-to-gitlab -s -mode commit
