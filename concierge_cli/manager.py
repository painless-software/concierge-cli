"""
Concierge repository projects management CLI.
"""
from gitlab import Gitlab
from gitlab.config import GitlabConfigMissingError

from .adapter import GroupMembership, Project
from .constants import GITLAB_DEFAULT_URI


class GitlabAPI:
    """
    Establishes an API connection to a GitLab instance.
    """

    def __init__(self, uri=None, token=None):
        """
        Connects to a GitLab instance using connection details from one of the
        local configuration files (see https://python-gitlab.readthedocs.io >
        Configuration > Files). Connects to GitLab.com by default if no config
        file is found. Specify an URI to override the config file lookup, the
        token is optional (anonymous access if none is supplied).
        """
        if not uri:
            try:
                self.api = Gitlab.from_config()
            except GitlabConfigMissingError:
                uri = GITLAB_DEFAULT_URI

        if uri:
            self.api = Gitlab(uri, private_token=token, per_page=100)


class TopicManager(GitlabAPI):
    """
    Manages topics on GitLab projects (visible in project settings).
    """

    def __init__(self, group_filter, project_filter, empty,
                 uri=None, token=None):
        """
        A topics filter by group, project and topic state (set or not set).
        """
        super().__init__(uri, token)
        self.group_filter = group_filter
        self.project_filter = project_filter
        self.empty = empty

    def projects(self):
        """
        List all projects and their topics, filtered by an optional
        search pattern.
        """
        for group in self.api.groups.list(search=self.group_filter, all=True):
            for group_project in \
                    group.projects.list(search=self.project_filter, all=True):
                project = Project(self.api, group_project)
                if (self.empty and not project.topic_count) or \
                        (not self.empty and project.topic_count):
                    yield project

    def show(self):
        """Display all found projects and their topics."""
        for project in self.projects():
            project.show_topics()

    def set(self, new_topics):
        """Set a list of topics on the projects found."""
        for project in self.projects():
            project.set_topics(new_topics)


class ProjectManager(GitlabAPI):
    """
    Retrieves information about GitLab projects.
    """

    def __init__(self, group_filter, project_filter, topic_list,
                 uri=None, token=None):
        """
        A projects filter by group, project and topic(s).
        """
        super().__init__(uri, token)
        self.group_filter = group_filter
        self.project_filter = project_filter
        self.topic_list = topic_list

    def projects(self):
        """
        List all projects and their topics, filtered by an optional
        search pattern.
        """
        for group in self.api.groups.list(search=self.group_filter, all=True):
            for group_project in \
                    group.projects.list(search=self.project_filter, all=True):
                project = Project(self.api, group_project)
                matched_tags = set(project.topic_list) & set(self.topic_list)
                if matched_tags or not self.topic_list:
                    yield project

    def show(self):
        """Display all found projects as a YAML list."""
        for project in self.projects():
            print(f"- {project}")


class GroupManager(GitlabAPI):
    """
    Manages permissions for users on GitLab project groups (= namespaces).
    """

    def __init__(self, group_filter, username, is_member=True,
                 uri=None, token=None):
        """
        A groups filter by group, project and topic(s).
        """
        super().__init__(uri, token)

        users = self.api.users.list(username=username)
        if len(users) != 1:
            raise ValueError('No such user: %s' % username)

        self.group_filter = group_filter
        self.user = users[0]
        self.is_member = is_member

    def groups(self):
        """
        List all groups and the current access level for our user,
        filtered by an optional search pattern.
        """
        for group in self.api.groups.list(search=self.group_filter, all=True):

            group_user = GroupMembership(group, self.user)

            if (not group_user.is_member and not self.is_member) or \
                    (group_user.is_member and self.is_member):
                yield group_user

    def show(self):
        """
        Display all found groups and the user's current access level.
        """
        for group_user in self.groups():
            print(group_user)

    def set(self, permission_name):
        """
        Ensure the user has privileges to access the selected groups.
        """
        for group_user in self.groups():
            group_user.set_membership(permission_name)