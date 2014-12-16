# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('group_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='auth.Group')),
                ('slug', models.SlugField(max_length=64)),
                ('description', models.TextField()),
            ],
            options={
            },
            bases=('auth.group',),
        ),
        migrations.CreateModel(
            name='Notice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('message', models.TextField(verbose_name='message')),
                ('added', models.DateTimeField(auto_now_add=True, verbose_name='added')),
                ('unseen', models.BooleanField(default=True, verbose_name='unseen')),
                ('archived', models.BooleanField(default=False, verbose_name='archived')),
                ('on_site', models.BooleanField(verbose_name='on site')),
                ('related_object_id', models.IntegerField(null=True, verbose_name='related object', blank=True)),
            ],
            options={
                'ordering': ['-added'],
                'verbose_name': 'notice',
                'verbose_name_plural': 'notices',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NoticeLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=64)),
                ('slug', models.SlugField(max_length=32)),
                ('description', models.TextField(verbose_name='description')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NoticeQueueBatch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pickled_data', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NoticeSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('medium', models.CharField(max_length=100, verbose_name='medium', choices=[(b'email', 'Email')])),
                ('send', models.BooleanField(verbose_name='send')),
                ('on_site', models.BooleanField(default=True, verbose_name='on site')),
            ],
            options={
                'verbose_name': 'notice setting',
                'verbose_name_plural': 'notice settings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NoticeType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(unique=True, max_length=40, verbose_name='label')),
                ('display', models.CharField(max_length=100, verbose_name='display')),
                ('description', models.TextField(verbose_name='description')),
                ('slug', models.CharField(max_length=40, verbose_name='template folder slug', blank=True)),
                ('default', models.IntegerField(verbose_name='default')),
                ('level', models.ForeignKey(blank=True, to='notification.NoticeLevel', null=True)),
            ],
            options={
                'verbose_name': 'notice type',
                'verbose_name_plural': 'notice types',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ObservedItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('added', models.DateTimeField(auto_now_add=True, verbose_name='added')),
                ('signal', models.TextField(verbose_name='signal')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('notice_type', models.ForeignKey(verbose_name='notice type', to='notification.NoticeType')),
                ('user', models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-added'],
                'verbose_name': 'observed item',
                'verbose_name_plural': 'observed items',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='noticesetting',
            name='notice_type',
            field=models.ForeignKey(verbose_name='notice type', to='notification.NoticeType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='noticesetting',
            name='user',
            field=models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='noticesetting',
            unique_together=set([('user', 'notice_type', 'medium')]),
        ),
        migrations.AddField(
            model_name='notice',
            name='notice_type',
            field=models.ForeignKey(verbose_name='notice type', to='notification.NoticeType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='notice',
            name='recipient',
            field=models.ForeignKey(related_name=b'recieved_notices', verbose_name='recipient', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='notice',
            name='sender',
            field=models.ForeignKey(related_name=b'sent_notices', verbose_name='sender', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='group',
            name='notice_types',
            field=models.ManyToManyField(help_text=b'The notice types that this group should receive.', related_name=b'groups', to='notification.NoticeType'),
            preserve_default=True,
        ),
    ]
