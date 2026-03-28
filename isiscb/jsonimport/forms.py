from django import forms

class UploadJsonDataForm(forms.Form):
    file = forms.FileField()