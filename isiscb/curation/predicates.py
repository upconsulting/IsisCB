from rules.predicates import predicate

@predicate
def is_accessible_by_dataset(user, object):
    # get roles from user
    # get dataset permissions from user
    # check if object is in dataset
