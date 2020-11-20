from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# Create your models here.
class Stock(models.Model):
    ticker = models.CharField(max_length=10, primary_key = True)
    info = models.JSONField()
    price = models.JSONField()
    query_date = models.DateField()

    def __str__(self):
        return 'ticker="' + self.ticker + '"' + str(self.query_date)

