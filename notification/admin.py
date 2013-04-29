from django.contrib import admin
from notification.models import NoticeType, NoticeSetting, Notice, ObservedItem, NoticeQueueBatch, NoticeLevel, Group
from django.contrib.auth.admin import GroupAdmin as AuthGroupAdmin

class NoticeLevelAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'description')

class NoticeTypeAdmin(admin.ModelAdmin):
    list_display = ('label', 'display', 'level', 'description', 'default')

class NoticeSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notice_type', 'medium', 'send')

class NoticeAdmin(admin.ModelAdmin):
    list_display = ('message', 'recipient', 'sender', 'notice_type', 'added', 'unseen', 'archived')

class GroupAdmin(AuthGroupAdmin):
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('permissions',)
    list_display = ['name' ,'slug' ,'description']
    search_fields = ['name']
    fields = ('name', 'slug', 'description', 'notice_types')

admin.site.register(NoticeLevel, NoticeLevelAdmin)
admin.site.register(NoticeQueueBatch)
admin.site.register(NoticeType, NoticeTypeAdmin)
admin.site.register(NoticeSetting, NoticeSettingAdmin)
admin.site.register(Notice, NoticeAdmin)
admin.site.register(ObservedItem)
admin.site.register(Group, GroupAdmin)
