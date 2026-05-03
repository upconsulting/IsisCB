from django import forms

class UploadJsonDataForm(forms.Form):
    citations_file = forms.FileField()
    authorities_file = forms.FileField()