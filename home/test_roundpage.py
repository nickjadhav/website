from datetime import datetime, timedelta, timezone, date
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from reversion.models import Version
import unittest

from . import models
from .factories import MentorApprovalFactory
from .factories import ProjectFactory


# don't try to use the static files manifest during tests
@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class RoundPageTestCase(TestCase):
    def test_round_closed_no_new_round(self):
        # Make a round where the internship start date was a month ago
        # Make an approved project in an approved community that is under that round
        past = datetime.now(timezone.utc) - timedelta(days=30)
        project_title = "AAAAAAAAHHHHHHH! This is a bug!!"
        community_name = "AAAAAAAAHHHHHHH! This is a community name!!"
        past_project = ProjectFactory(
                approval_status=models.ApprovalStatus.APPROVED,
                project_round__approval_status=models.ApprovalStatus.APPROVED,
                project_round__community__name=community_name,
                short_title=project_title,
                project_round__participating_round__start_from='internstarts',
                project_round__participating_round__start_date=past)

        # Grab the current project selection page
        response = self.client.post(reverse('project-selection'))
        # Page should return a normal status code of 200
        # Make sure that the contents don't include the approved project title from last round
        self.assertNotContains(response, project_title, status_code=200)

        # Grab the community and project CFP page
        response = self.client.post(reverse('community-cfp'))
        # Make sure that the contents don't include the community as currently participating
        self.assertNotContains(response, 'review the list of participating communities below who are looking for help', status_code=200)
        # Make sure the page shows the community as a past approved community
        self.assertContains(response, community_name, status_code=200)

    # XXX: FIXME - this test case looks fine when I recreate it in my local database
    # and log in as a mentor with a pending project.
    # However, the test case fails, showing both pending and approved project.
    # It also shows "Project details are hidden.The details may be hidden because\nyou haven\'t completed an initial application."
    # I suspect something is wrong with setting up the projects or mentors,
    # but I don't know what.
    @unittest.expectedFailure
    def test_mentor_sees_hidden_projects(self):
        # Before the Outreachy application period opens,
        # We allow mentors with an approved project in an approved community
        # to see all other approved projects (even if it's not in their community).
        # Mentors with pending projects should only see their own project.
        future = datetime.now(timezone.utc) - timedelta(days=10)
        pending_project_title = "AAAAAAAAHHHHHHH! This project is pending!!"
        pending_mentor_approval = MentorApprovalFactory(
                approval_status=models.ApprovalStatus.APPROVED,
                project__approval_status=models.ApprovalStatus.PENDING,
                project__project_round__approval_status=models.ApprovalStatus.APPROVED,
                project__short_title=pending_project_title,
                project__project_round__participating_round__start_from='appsopen',
                project__project_round__participating_round__start_date=future)

        # Make a different mentor with an approved project under the same community
        approved_project_title = "AAAAAAAAHHHHHHH! This project is approved!!"
        approved_mentor_approval = MentorApprovalFactory(
                approval_status=models.ApprovalStatus.APPROVED,
                project__approval_status=models.ApprovalStatus.APPROVED,
                project__project_round=pending_mentor_approval.project.project_round,
                project__short_title=approved_project_title)

        # Login as the pending mentor
        self.client.force_login(pending_mentor_approval.mentor.account)

        response = self.client.post(reverse('project-selection'))
        # Make sure that the contents does include the mentor's pending project title
        self.assertContains(response, '<h2>Your Pending Outreachy Internship Projects</h2>', status_code=200)
        self.assertContains(response, pending_project_title, status_code=200)
        # Make sure that the contents does not include the other mentor's approved project title
        #print(response.content)
        self.assertNotContains(response, approved_project_title, status_code=200)

        # Login as the approved mentor
        self.client.force_login(pending_mentor_approval.mentor.account)

        response = self.client.post(reverse('project-selection'))
        # Make sure that the contents does include the mentor's approved project title
        self.assertContains(response, approved_project_title, status_code=200)
        # Make sure that the contents does not include the other mentor's pending project title
        self.assertNotContains(response, pending_project_title, status_code=200)

        # TODO:
        # Set the pending project to approved and make sure both mentors can see both projects
        # Make a mentor who is approved under a different community
        # Make sure that mentor can see all three projects
        # Make sure all three mentors can see all projects on all community landing pages

    def test_application_round_open(self):
        # Make a round where the application period is open
        # Make an approved project in an approved community
        open_date = datetime.now(timezone.utc) - timedelta(days=10)
        project_title = "AAAAAAAAHHHHHHH! The code works!!"
        community_name = "AAAAAAAAHHHHHHH! This is a community name!!"
        past_project = ProjectFactory(
                approval_status=models.ApprovalStatus.APPROVED,
                project_round__approval_status=models.ApprovalStatus.APPROVED,
                project_round__community__name=community_name,
                short_title=project_title,
                project_round__participating_round__start_from='appsopen',
                project_round__participating_round__start_date=open_date)

        # Grab the current project selection page
        response = self.client.post(reverse('project-selection'))
        # Page should return a normal status code of 200
        # Make sure that the contents does include the approved project title from this round
        self.assertContains(response, project_title, status_code=200)
        # Since the project has an on-time deadline it should still be open
        self.assertContains(response, '<h2 id="open-projects">Outreachy Open Projects</h2>', status_code=200)

        # Grab the community and project CFP page
        response = self.client.post(reverse('community-cfp'))
        # Make sure it includes the community as currently participating
        self.assertContains(response, 'review the list of participating communities below who are looking for help', status_code=200)
        # Make sure the page shows the community
        self.assertContains(response, community_name, status_code=200)
