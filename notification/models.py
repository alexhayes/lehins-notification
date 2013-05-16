import importlib

try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.db import models
from django.db.models.query import QuerySet
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import render_to_string

from django.core.exceptions import ImproperlyConfigured

from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext, get_language, activate

from notification.backends import get_backends, get_backend

from django.contrib.auth.models import Group as AuthGroup

"""
    subject.txt and message.txt can be put either in notification/noticetype_label/media_slug or notification/noticetype_label/
    or notification/
"""

CONTEXT_PROCESSORS = getattr(
    settings, "NOTIFICATION_CONTEXT_PROCESSORS", None)

QUEUE_ALL = getattr(settings, "NOTIFICATION_QUEUE_ALL", False)
USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class LanguageStoreNotAvailable(Exception):
    pass


class NoticeLevel(models.Model):
    title = models.CharField(max_length=64)
    slug = models.SlugField(max_length=32)
    description = models.TextField(_('description'))
    
    def __unicode__(self):
        return self.title

class NoticeType(models.Model):
    label = models.CharField(_('label'), max_length=40, unique=True)
    display = models.CharField(_('display'), max_length=100)
    level = models.ForeignKey(NoticeLevel, null=True, blank=True)
    description = models.TextField(_('description'))
    slug = models.CharField(_('template folder slug'), max_length=40, blank=True)

    # by default only on for media with sensitivity less than or equal to this number
    default = models.IntegerField(_('default'))

    def __unicode__(self):
        return self.display

    class Meta:
        verbose_name = _("notice type")
        verbose_name_plural = _("notice types")

    @property
    def template_slug(self):
        return self.slug or self.label


class NoticeMediaListChoices():
    """
        Iterator used to delay getting the NoticeSetting medium choices list until required
        (and when the other medium have been registered).
    """

    def __init__(self):
        self.index = -1

    def __iter__(self):
        return self

    def next(self):
        self.index += 1
        try:
            item = get_backends()[self.index]
        except IndexError:
            raise StopIteration
        else:
            return (item.slug, item.title)


class NoticeSetting(models.Model):
    """
    Indicates, for a given user, whether to send notifications
    of a given type to a given medium.
    """
    user = models.ForeignKey(USER_MODEL, verbose_name=_("user"))
    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))
    medium = models.CharField(_('medium'), max_length=100, choices=NoticeMediaListChoices())
    send = models.BooleanField(_('send'))
    on_site = models.BooleanField(_('on site'), default=True)

    class Meta:
        verbose_name = _("notice setting")
        verbose_name_plural = _("notice settings")
        unique_together = ("user", "notice_type", "medium")

    def __unicode__(self):
        return self.medium


def create_notification_setting(user, notice_type, medium):
    default = (get_backend(medium).sensitivity <= notice_type.default)
    setting = NoticeSetting(
        user=user, notice_type=notice_type, medium=medium, send=default)
    setting.save()
    return setting

def get_notification_setting(user, notice_type, medium):
    try:
        return NoticeSetting.objects.get(
            user=user, notice_type=notice_type, medium=medium)
    except NoticeSetting.DoesNotExist:
        return create_notification_setting(user, notice_type, medium)

def get_notification_settings(user, notification_label):
    """
        Gets NoticeSettings for notification_label and user for all medium registered.
        Created Default ones if there is nothing.
        Raises DoesNotExist for wrong label.
    """
    result = NoticeSetting.objects.filter(
        user=user, notice_type__label=notification_label)
    if not result:
        notice_type = NoticeType.objects.get(label=notification_label)
        for id, medium in NoticeMediaListChoices():
            create_notification_setting(
                user=user, notice_type=notice_type, medium=unicode(medium).lower())
        result = NoticeSetting.objects.filter(
            user=user, notice_type__label=notification_label)
    return result

def should_send(user, notice_type, medium):
    return get_notification_setting(user, notice_type, medium).send


class NoticeManager(models.Manager):

    def notices_for(self, user, archived=False, unseen=None, on_site=None, sent=False):
        """
        returns Notice objects for the given user.

        If archived=False, it only include notices not archived.
        If archived=True, it returns all notices for that user.

        If unseen=None, it includes all notices.
        If unseen=True, return only unseen notices.
        If unseen=False, return only seen notices.
        """
        if sent:
            lookup_kwargs = {"sender": user}
        else:
            lookup_kwargs = {"recipient": user}
        qs = self.filter(**lookup_kwargs)
        if not archived:
            self.filter(archived=archived)
        if unseen is not None:
            qs = qs.filter(unseen=unseen)
        if on_site is not None:
            qs = qs.filter(on_site=on_site)
        return qs

    def unseen_count_for(self, recipient, **kwargs):
        """
        returns the number of unseen notices for the given user but does not
        mark them seen
        """
        return self.notices_for(recipient, unseen=True, **kwargs).count()

    def received(self, recipient, **kwargs):
        """
        returns notices the given recipient has recieved.
        """
        kwargs["sent"] = False
        return self.notices_for(recipient, **kwargs)

    def sent(self, sender, **kwargs):
        """
        returns notices the given sender has sent
        """
        kwargs["sent"] = True
        return self.notices_for(sender, **kwargs)

class Notice(models.Model):
    recipient = models.ForeignKey(USER_MODEL, related_name="recieved_notices", verbose_name=_("recipient"))
    sender = models.ForeignKey(USER_MODEL, null=True, related_name="sent_notices", verbose_name=_("sender"), blank=True)
    message = models.TextField(_('message'))
    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))
    added = models.DateTimeField(_('added'), auto_now_add=True)
    unseen = models.BooleanField(_('unseen'), default=True)
    archived = models.BooleanField(_('archived'), default=False)
    on_site = models.BooleanField(_('on site'))
    related_object_id = models.IntegerField(_('related object'), null=True, blank=True)

    objects = NoticeManager()

    def __unicode__(self):
        return self.message

    def archive(self):
        self.archived = True
        self.save()

    def is_unseen(self):
        """
        returns value of self.unseen but also changes it to false.

        Use this in a template to mark an unseen notice differently the first
        time it is shown.
        """
        unseen = self.unseen
        if unseen:
            self.unseen = False
            self.save()
        return unseen

    class Meta:
        ordering = ["-added"]
        verbose_name = _("notice")
        verbose_name_plural = _("notices")

    def get_absolute_url(self):
        return reverse("notification_notice", args=[str(self.pk)])

    def get_absolute_url(self):
        return ("notification_notice", [str(self.pk)])
    get_absolute_url = models.permalink(get_absolute_url)


class NoticeQueueBatch(models.Model):
    """
    A queued notice.
    Denormalized data for a notice.
    """
    pickled_data = models.TextField()

class Group(AuthGroup):
    """
    Defines groups of users who should also receive particular notifications not directly sent to them.
    
    Kind of equivilent a cc list of users... kind of...
    """
    slug = models.SlugField(max_length=64)
    description = models.TextField()
    notice_types = models.ManyToManyField(NoticeType, related_name='groups', help_text='The notice types that this group should receive.')

def create_notice_type(label, display, description, default=2, verbosity=1, slug=''):
    """
    Creates a new NoticeType.

    This is intended to be used by other apps as a post_syncdb manangement step.
    """
    try:
        notice_type = NoticeType.objects.get(label=label)
        updated = False
        if display != notice_type.display:
            notice_type.display = display
            updated = True
        if description != notice_type.description:
            notice_type.description = description
            updated = True
        if default != notice_type.default:
            notice_type.default = default
            updated = True
        if slug != notice_type.slug:
            notice_type.slug = slug
            updated = True
        if updated:
            notice_type.save()
            if verbosity > 1:
                print "Updated %s NoticeType" % label
    except NoticeType.DoesNotExist:
        notice_type = NoticeType.objects.create(label=label, display=display, description=description, default=default, slug=slug)
        if verbosity > 1:
            print "Created %s NoticeType" % label
    return notice_type

def get_notification_language(user):
    """
    Returns site-specific notification language for this user. Raises
    LanguageStoreNotAvailable if this site does not use translated
    notifications.
    """
    if getattr(settings, 'NOTIFICATION_LANGUAGE_MODULE', False):
        try:
            app_label, model_name = settings.NOTIFICATION_LANGUAGE_MODULE.split('.')
            model = models.get_model(app_label, model_name)
            language_model = model._default_manager.get(user__id__exact=user.id)
            if hasattr(language_model, 'language'):
                return language_model.language
        except (ImportError, ImproperlyConfigured, model.DoesNotExist):
            raise LanguageStoreNotAvailable
    raise LanguageStoreNotAvailable

def from_string_import(string):
    """
    Returns the attribute from a module, specified by a string.
    """
    module, attrib = string.rsplit('.', 1)
    return getattr(importlib.import_module(module), attrib)


def get_formatted_message(formats, notice_type, context, media_slug=None):
    """
    Returns a dictionary with the format identifier as the key. The values are
    are fully rendered templates with the given context.
    """
    format_templates = {}
    if context is None:
        context = {}
    if CONTEXT_PROCESSORS:
        for c_p in [from_string_import(x) for x in CONTEXT_PROCESSORS]:
            context.update(c_p())
    for format in formats:
        # conditionally turn off autoescaping for .txt extensions in format
        if format.endswith(".txt") or format.endswith(".html"):
            context.autoescape = False
        else:
            context.autoescape = True
        format_templates[format] = render_to_string((
            'notification/%s/%s/%s' % (
                    notice_type.template_slug, media_slug, format),
            'notification/%s/%s' % (notice_type.template_slug, format),
            'notification/%s/%s' % (media_slug, format),
            'notification/%s' % format), context_instance=context)
    return format_templates

def send_now(users, label, extra_context=None, on_site=None, sender=None, related_object_id=None, groups=True, backends=get_backends()):
    """
    Creates a new notice.

    This is intended to be how other apps create new notices.

    notification.send(user, "friends_invite_sent", {
        "spam": "eggs",
        "foo": "bar",
    )

    You can pass in on_site=False to prevent the notice emitted from being
    displayed on the site.
    """
    if extra_context is None:
        extra_context = {}

    notice_type = NoticeType.objects.get(label=label)

    protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
    current_site = Site.objects.get_current()

    current_language = get_language()

    if groups:
        # Only send to groups if groups is True
        for group in notice_type.groups.all():
            if isinstance(users, QuerySet):
                users = users | group.user_set.all()
            else:
                users += group.user_set.all()

    for user in users:
        # get user language for user from language store defined in
        # NOTIFICATION_LANGUAGE_MODULE setting
        try:
            language = get_notification_language(user)
        except LanguageStoreNotAvailable:
            language = None

        if language is not None:
            # activate the user's language
            activate(language)

        # update context with user specific translations
        context = Context({
            "recipient": user,
            "sender": sender,
            "notice": ugettext(notice_type.display),
            "current_site": current_site,
        })
        context.update(extra_context)
        
        messages = get_formatted_message(
            ['notice.html'], notice_type, context, 'notice')
        notice_setting = get_notification_setting(user, notice_type, 'email')
        if on_site is None:
            on_site = notice_setting.on_site
        notice = Notice.objects.create(
            recipient=user, message=messages['notice.html'], notice_type=notice_type,
            on_site=on_site, sender=sender, related_object_id=related_object_id)

        if len(backends) > 0 and isinstance(backends[0], str):
            backends = get_backends(backends)

        for backend in backends:
            send_user_notification(user, notice_type, backend, context)

    # reset environment to original language
    activate(current_language)

def send_user_notification(user, notice_type, backend, context):

    recipients = []

    # get prerendered format messages
    message = get_formatted_message(
        backend.formats, notice_type, context, backend.slug)

    if user.is_active and should_send(user, notice_type, backend.slug):
        recipients.append(user)

    if recipients:
        try:
            backend.send(message, recipients)
        except TypeError, e:
            print u"Tried to send notification to media %s. Send function raised an error." % (backend.title,)
            raise e


def send(*args, **kwargs):
    """
    A basic interface around both queue and send_now. This honors a global
    flag NOTIFICATION_QUEUE_ALL that helps determine whether all calls should
    be queued or not. A per call ``queue`` or ``now`` keyword argument can be
    used to always override the default global behavior.
    """
    queue_flag = kwargs.pop("queue", False)
    now_flag = kwargs.pop("now", False)
    celery_flag = kwargs.pop("async", False)
    assert not (queue_flag and now_flag), "'queue' and 'now' cannot both be True."
    if queue_flag:
        return queue(*args, **kwargs)
    elif now_flag:
        return send_now(*args, **kwargs)
    else:
        if QUEUE_ALL:
            return queue(*args, **kwargs)
        else:
            return send_now(*args, **kwargs)
        
def queue(users, label, extra_context=None, on_site=True, sender=None, related_object_id=None):
    """
    Queue the notification in NoticeQueueBatch. This allows for large amounts
    of user notifications to be deferred to a seperate process running outside
    the webserver.
    """
    if extra_context is None:
        extra_context = {}
    if isinstance(users, QuerySet):
        users = [row["pk"] for row in users.values("pk")]
    else:
        users = [user.pk for user in users]
        
    notice_type = NoticeType.objects.get(label=label)
    for group in notice_type.groups.all():
        if isinstance(users, QuerySet):
            users = users | group.user_set.all()
        else:
            users += group.user_set.all()

    notices = []
    for user in users:
        notices.append(
            (user, label, extra_context, on_site, sender, related_object_id))
    NoticeQueueBatch(pickled_data=pickle.dumps(notices).encode("base64")).save()

class ObservedItemManager(models.Manager):

    def all_for(self, observed, signal):
        """
        Returns all ObservedItems for an observed object,
        to be sent when a signal is emited.
        """
        content_type = ContentType.objects.get_for_model(observed)
        observed_items = self.filter(content_type=content_type, object_id=observed.id, signal=signal)
        return observed_items

    def get_for(self, observed, observer, signal):
        content_type = ContentType.objects.get_for_model(observed)
        observed_item = self.get(content_type=content_type, object_id=observed.id, user=observer, signal=signal)
        return observed_item


class ObservedItem(models.Model):
    user = models.ForeignKey(USER_MODEL, verbose_name=_("user"))

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    observed_object = generic.GenericForeignKey('content_type', 'object_id')

    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))

    added = models.DateTimeField(_('added'), auto_now_add=True)

    # the signal that will be listened to send the notice
    signal = models.TextField(verbose_name=_('signal'))

    objects = ObservedItemManager()

    class Meta:
        ordering = ["-added"]
        verbose_name = _("observed item")
        verbose_name_plural = _("observed items")

    def send_notice(self, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update({'observed': self.observed_object})
        send([self.user], self.notice_type.label, extra_context)

def observe(observed, observer, notice_type_label, signal='post_save'):
    """
    Create a new ObservedItem.

    To be used by applications to register a user as an observer for some object.
    """
    notice_type = NoticeType.objects.get(label=notice_type_label)
    observed_item = ObservedItem(user=observer, observed_object=observed,
                                 notice_type=notice_type, signal=signal)
    observed_item.save()
    return observed_item

def stop_observing(observed, observer, signal='post_save'):
    """
    Remove an observed item.
    """
    observed_item = ObservedItem.objects.get_for(observed, observer, signal)
    observed_item.delete()

def send_observation_notices_for(observed, signal='post_save', extra_context=None):
    """
    Send a notice for each registered user about an observed object.
    """
    if extra_context is None:
        extra_context = {}
    observed_items = ObservedItem.objects.all_for(observed, signal)
    for observed_item in observed_items:
        observed_item.send_notice(extra_context)
    return observed_items


def is_observing(observed, observer, signal="post_save"):
    if hasattr(observer, 'is_anonymous') and observer.is_anonymous():
        return False
    try:
        observed_items = ObservedItem.objects.get_for(observed, observer, signal)
        return True
    except ObservedItem.DoesNotExist:
        return False
    except ObservedItem.MultipleObjectsReturned:
        return True

def handle_observations(sender, instance, *args, **kw):
    send_observation_notices_for(instance)

