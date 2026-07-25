from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("graph", "0002_overlay_models"),
    ]

    operations = [
        migrations.RenameModel("Workspace", "ProjectMap"),
        migrations.RenameField("NodeOverlay", "workspace", "project_map"),
        migrations.RenameField("EdgeOverlay", "workspace", "project_map"),
        migrations.AddField(
            model_name="projectmap",
            name="project_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=100,
                null=True,
                unique=True,
            ),
        ),
    ]
