# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notice',
            name='on_site',
            field=models.BooleanField(default=False, verbose_name='on site'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='noticesetting',
            name='send',
            field=models.BooleanField(default=False, verbose_name='send'),
            preserve_default=True,
        ),
    ]
