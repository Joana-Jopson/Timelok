from django import forms
from .models import EmployeeMaster, Organization, Grade, Designation, EmployeeType, Country, Location, ContractorCompany,ChatMessage


class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ['message_text', 'file_path']
        widgets = {
            'message_text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Type a message...'}),
        }
