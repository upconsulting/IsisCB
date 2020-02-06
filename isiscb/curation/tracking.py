from isisdata.models import *


class TrackingWorkflow(object):
    """
    This class represents the tracking workflow a record goes through.
    """
    # Don't forget! Update curation/static/curation/js/bulktracking.js
    transitions = (
        (None, Tracking.FULLY_ENTERED),
        (Tracking.NONE, Tracking.FULLY_ENTERED),
        (Tracking.FULLY_ENTERED, Tracking.PROOFED),
        (Tracking.PROOFED, Tracking.AUTHORIZED),
        (Tracking.AUTHORIZED, Tracking.PRINTED),
        (Tracking.PRINTED, Tracking.HSTM_UPLOAD),
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
    
