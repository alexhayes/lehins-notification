from django.utils.translation import ugettext_lazy as _

from notification.backends.base import NotificationBackend
from push_notifications.models import APNSDevice, GCMDevice

import json
import copy

class MobileBackend(NotificationBackend):
    """
    Mobile (IOS/Android) delivery backend.
    """

    title = _("Mobile")
    slug = 'mobile'
    formats = ('message.txt',)

    def get_devices(self, recipients):
        devices = []
        for recipient in recipients:
            for dev_ios in APNSDevice.objects.filter(user=recipient):
                devices.append(dev_ios)
            for dev_android in GCMDevice.objects.filter(user=recipient):
                devices.append(dev_android)

        return devices

    def send(self, message, recipients, *args, **kwargs):
        msg = message['message.txt']
        devices = self.get_devices(recipients)
        json_msg = json.loads(msg)
        
        for dev in devices:
            msg_dev = copy.copy(json_msg)
            if isinstance(dev, APNSDevice):
                del msg_dev['msg']
            else:
                del msg_dev['aps']
                
            dev.send_message(msg_dev)
        return True

