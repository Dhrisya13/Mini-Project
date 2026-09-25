from django.db import models

from django.contrib.auth.models import User


class User_table(models.Model):
    LOGIN=models.ForeignKey(User,on_delete=models.CASCADE)
    Full_name=models.TextField()
    DOB=models.DateField()
    Gender=models.TextField()
    Email=models.TextField()
    PhonenNo=models.BigIntegerField()

class Health_record(models.Model):
    User_ID=models.ForeignKey(User_table,on_delete=models.CASCADE)
    Height=models.FloatField()
    Weight=models.FloatField()
    Smoking=models.TextField()
    Alcohol=models.TextField()
    Physical_Activity=models.TextField()
    Sleep_Duration=models.FloatField()
    Water_Intake=models.FloatField()

class Prediction_Details(models.Model):
    Record_ID=models.ForeignKey(Health_record,on_delete=models.CASCADE)
    Pregnancies=models.IntegerField()
    Glucose=models.FloatField()
    Blood_Pressure=models.FloatField()
    Skin_Thickness=models.FloatField()
    Insulin=models.FloatField()
    Diabetes_pedigree=models.FloatField()

class Prediction_Risk(models.Model):
    Prediction_ID=models.ForeignKey(Prediction_Details,on_delete=models.CASCADE)
    Risk_level=models.TextField()
    Prediction_date=models.DateField()

class Reccomendation_table(models.Model):
    Risk_ID=models.ForeignKey(Prediction_Risk,models.CASCADE)
    Diet_plan=models.TextField()
    Exercise_plan=models.TextField()
    Water_intake=models.TextField()
    Sleep_intake=models.TextField()
    weight_management=models.TextField()

# class Health_History(models.Model):
#     User_ID = models.ForeignKey(User_table, on_delete=models.CASCADE)
#     Prediction_ID = models.ForeignKey(Prediction_Details, on_delete=models.CASCADE)

class Educational_content(models.Model):
    Title=models.TextField()
    Category=models.TextField()
    Description=models.TextField()


