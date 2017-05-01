from isisdata.models import *


class TrackingWorkflow(object):
    """
    This class represents the tracking workflow a record goes through.
    """


    transitions = (
        (None, Tracking.BULK_DATA),
        (Tracking.NONE, Tracking.BULK_DATA),
        (Tracking.BULK_DATA, Tracking.FULLY_ENTERED),
        (None, Tracking.FULLY_ENTERED),
        (Tracking.NONE, Tracking.FULLY_ENTERED),
        (Tracking.FULLY_ENTERED, Tracking.PROOFED),
        (Tracking.PROOFED, Tracking.AUTHORIZED),
        (Tracking.AUTHORIZED, Tracking.HSTM_UPLOAD),
        (Tracking.AUTHORIZED, Tracking.PRINTED),
    )

    def __init__(self, instance):
        self.tracked_object = instance
        self.entries = [x.type_controlled for x in instance.tracking_records.all()]
        self.instance = instance

    @classmethod
    def allowed(cls, action):
        return zip(*filter(lambda (start, end): end == action, cls.transitions))[0]

    def is_workflow_action_allowed(self, action):
        return self.instance.tracking_state in TrackingWorkflow.allowed(action) and action not in self.entries
