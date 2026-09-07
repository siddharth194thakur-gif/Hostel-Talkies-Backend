from django.db import migrations


def create_competition_tables_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    Competition = apps.get_model('gaming', 'Competition')
    CompetitionParticipant = apps.get_model('gaming', 'CompetitionParticipant')
    CompetitionResult = apps.get_model('gaming', 'CompetitionResult')

    if Competition._meta.db_table not in existing_tables:
        schema_editor.create_model(Competition)
        existing_tables.add(Competition._meta.db_table)

    if CompetitionParticipant._meta.db_table not in existing_tables:
        schema_editor.create_model(CompetitionParticipant)
        existing_tables.add(CompetitionParticipant._meta.db_table)

    if CompetitionResult._meta.db_table not in existing_tables:
        schema_editor.create_model(CompetitionResult)
        existing_tables.add(CompetitionResult._meta.db_table)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gaming', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_competition_tables_if_missing,
            reverse_code=noop,
        ),
    ]
