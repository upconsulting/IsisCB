from haystack import utils

def get_isiscb_identifier(obj_or_string):
    if type(obj_or_string).__name__ == 'Citation':
        return obj_or_string.id

    return utils.default_get_identifier(obj_or_string)
