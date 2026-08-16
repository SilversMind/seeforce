from django.test import TestCase
from apps.graph.models import ProjectMap, LexiconEntry


class LexiconEntryModelTest(TestCase):
    def setUp(self):
        self.pm = ProjectMap.objects.create(name="Test", source_json={})

    def test_create_entry(self):
        entry = LexiconEntry.objects.create(
            project_map=self.pm, term="SM83", definition="Sharp SM83 processor"
        )
        self.assertEqual(entry.term, "SM83")
        self.assertEqual(entry.definition, "Sharp SM83 processor")

    def test_unique_term_per_project(self):
        LexiconEntry.objects.create(project_map=self.pm, term="CPU", definition="Central Processing Unit")
        with self.assertRaises(Exception):
            LexiconEntry.objects.create(project_map=self.pm, term="CPU", definition="Different")

    def test_same_term_different_projects(self):
        pm2 = ProjectMap.objects.create(name="Other", source_json={})
        LexiconEntry.objects.create(project_map=self.pm, term="CPU", definition="A")
        entry2 = LexiconEntry.objects.create(project_map=pm2, term="CPU", definition="B")
        self.assertEqual(entry2.term, "CPU")
