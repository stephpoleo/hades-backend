from django.db import models

class EDS(models.Model):
    id_eds_pk = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=65, null=True, blank=True)
    plaza = models.CharField(max_length=20, null=True, blank=True)
    state = models.CharField(max_length=20, null=True, blank=True)
    municipality = models.CharField(max_length=35, null=True, blank=True)
    zip_code = models.CharField(max_length=10, null=True, blank=True)
    plaza_status = models.BooleanField(null=True, blank=True)
    long_eds = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    latit_eds = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)

    class Meta:
        db_table = 'EDS'