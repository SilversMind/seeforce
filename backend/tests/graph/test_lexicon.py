from django.test import TestCase
from apps.graph.models import ProjectMap, LexiconEntry
import json


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


class LexiconAPITest(TestCase):
    def setUp(self):
        self.pm = ProjectMap.objects.create(name="Project", source_json={})

    def test_list_empty(self):
        res = self.client.get(f"/api/graph/{self.pm.id}/lexicon/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_upsert_creates_entry(self):
        res = self.client.post(
            f"/api/graph/{self.pm.id}/lexicon/",
            data=json.dumps({"term": "SM83", "definition": "Sharp SM83 processor"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"ok": True})
        self.assertEqual(LexiconEntry.objects.filter(project_map=self.pm).count(), 1)

    def test_upsert_updates_existing(self):
        LexiconEntry.objects.create(project_map=self.pm, term="CPU", definition="Old")
        res = self.client.post(
            f"/api/graph/{self.pm.id}/lexicon/",
            data=json.dumps({"term": "CPU", "definition": "New definition"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(LexiconEntry.objects.get(project_map=self.pm, term="CPU").definition, "New definition")

    def test_list_returns_entries(self):
        LexiconEntry.objects.create(project_map=self.pm, term="PPU", definition="Pixel Processing Unit")
        LexiconEntry.objects.create(project_map=self.pm, term="APU", definition="Audio Processing Unit")
        res = self.client.get(f"/api/graph/{self.pm.id}/lexicon/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 2)
        terms = {e["term"] for e in data}
        self.assertIn("PPU", terms)
        self.assertIn("APU", terms)

    def test_delete_entry(self):
        LexiconEntry.objects.create(project_map=self.pm, term="DMA", definition="Direct Memory Access")
        res = self.client.delete(f"/api/graph/{self.pm.id}/lexicon/DMA/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(LexiconEntry.objects.filter(project_map=self.pm, term="DMA").count(), 0)

    def test_delete_unknown_returns_404(self):
        res = self.client.delete(f"/api/graph/{self.pm.id}/lexicon/UNKNOWN/")
        self.assertEqual(res.status_code, 404)

    def test_upsert_missing_term_returns_400(self):
        res = self.client.post(
            f"/api/graph/{self.pm.id}/lexicon/",
            data=json.dumps({"definition": "Missing term"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
