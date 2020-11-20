from django import forms


class StockForm(forms.Form):
    symbol = forms.CharField(max_length = 10, label='Stock Ticker', widget=forms.TextInput(attrs={'placeholder': 'Enter Stock Ticker', 'class': 'form-control mr-sm-2'}))
    