from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Address, Profile

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100, required=False)
    email = forms.EmailField()

    class Meta:
        model = Profile
        fields = ('phone', 'avatar', 'date_of_birth', 'newsletter_opt_in')
        widgets = {'date_of_birth': forms.DateInput(attrs={'type': 'date'})}


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ('user', 'created_at', 'updated_at')
        widgets = {
            'address_type': forms.Select(attrs={'class': 'fx-input'}),
        }
