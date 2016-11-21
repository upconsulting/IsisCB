from isisdata.models import *

import collections

class TrackingWorkflow(object):
    """
    This class represents the tracking workflow a record goes through.
    """

    stages = collections.OrderedDict()
    stages[None] = Tracking.FULLY_ENTERED
    stages[Tracking.FULLY_ENTERED] = Tracking.PROOFED
    stages[Tracking.PROOFED] = Tracking.AUTHORIZED

    next_stage = None

    def __init__(self, instance):
        self.tracked_object = instance

        self.entries = [x.type_controlled for x in instance.tracking_entries.all()]

        if not self.entries:
            self.next_stage = self.stages[None]

        for key, value in self.stages.items():
            if key in self.entries:
                self.next_stage = value

    def is_workflow_action_allowed(self, action):
        return action == self.next_stage and action not in self.entries
