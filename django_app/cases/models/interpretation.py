from django.db import models

from django_synergy.devices.models import DeviceSettings
from django_synergy.devices.utils import APNEA_LIST, BRADYCARDIA_LIST, TACHYCARDIA_LIST, HIGHSPO2_LIST, LOWSPO2_LIST, \
    DOWNLOADFREQUENCY_LIST
from django_synergy.interpretation_libraries.models import InterpretationDiagnosis, Utilization, EventRecording, \
    Interpretation, InterpretationNotes1, InterpretationNotes2, InterpretationNotes3, InterpretationNotes4, \
    Recommendation, RecommendationNotes1, RecommendationNotes2
from django_synergy.cases.models import Case
from django_synergy.utils.models import AbstractBaseModel
from django_extensions.db.fields import AutoSlugField, slugify


class InterpretationData(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'case__case_no', 'date_from', 'date_to'], slugify_function=slugify)
    case = models.ForeignKey(
        Case, related_name='data_interpretation_case', on_delete=models.PROTECT)
    date_from = models.DateField()
    date_to = models.DateField()
    no_of_events = models.IntegerField()
    diagnosis = models.ForeignKey(
        InterpretationDiagnosis, related_name='data_interpretation_diagnosis', on_delete=models.PROTECT, null=True,
        blank=True)
    interpretation_comments = models.TextField(null=True, blank=True)
    event_recording = models.ForeignKey(
        EventRecording, related_name='data_interpretation_event_recording', on_delete=models.PROTECT, null=True,
        blank=True)
    interpretation = models.ForeignKey(
        Interpretation, related_name='data_interpretation', on_delete=models.PROTECT, null=True, blank=True)
    interpretation_notes1 = models.ForeignKey(
        InterpretationNotes1, related_name='data_interpretation_notes_1', on_delete=models.PROTECT, null=True,
        blank=True)
    interpretation_notes2 = models.ForeignKey(
        InterpretationNotes2, related_name='data_interpretation_notes_2', on_delete=models.PROTECT, null=True,
        blank=True)
    interpretation_notes3 = models.ForeignKey(
        InterpretationNotes3, related_name='data_interpretation_notes_3', on_delete=models.PROTECT, null=True,
        blank=True)
    interpretation_notes4 = models.ForeignKey(
        InterpretationNotes4, related_name='data_interpretation_notes_4', on_delete=models.PROTECT, null=True,
        blank=True)

    utilization = models.ForeignKey(
        Utilization, related_name='data_interpretation_utilization', on_delete=models.PROTECT, null=True, blank=True)
    recommendation = models.ForeignKey(
        Recommendation, related_name='data_interpretation_recommendation', on_delete=models.PROTECT, null=True,
        blank=True)
    recommendation_notes1 = models.ForeignKey(
        RecommendationNotes1, related_name='data_interpretation_recommendation_notes1', on_delete=models.PROTECT,
        null=True, blank=True)
    recommendation_notes2 = models.ForeignKey(
        RecommendationNotes2, related_name='data_interpretation_recommendation_notes2', on_delete=models.PROTECT,
        null=True, blank=True)
    recommendation_comments = models.TextField(null=True, blank=True)

    change_device_settings = models.BooleanField(default=False, null=True)
    apnea_alarm = models.CharField(choices=APNEA_LIST, max_length=50, null=True, blank=True)
    bradycardia_alarm = models.CharField(choices=BRADYCARDIA_LIST, max_length=50, null=True, blank=True)
    tachycardia_alarm = models.CharField(choices=TACHYCARDIA_LIST, max_length=50, null=True, blank=True)
    high_spo2 = models.CharField(choices=HIGHSPO2_LIST, max_length=50, null=True, blank=True)
    low_spo2 = models.CharField(choices=LOWSPO2_LIST, max_length=50, null=True, blank=True)
    download_frequency = models.CharField(choices=DOWNLOADFREQUENCY_LIST, max_length=50, null=True, blank=True)
    change_therapy = models.BooleanField(default=False, null=True)
    change_oxygen_therapy = models.TextField(null=True, blank=True)
    change_caffeine_therapy = models.TextField(null=True, blank=True)
    discontinue_case = models.BooleanField(default=False, null=True)
    other = models.BooleanField(default=False, null=True)
    physician_comments = models.TextField(null=True, blank=True)

    device_settings = models.ForeignKey(DeviceSettings, related_name="interpretation_device_settings",
                                        on_delete=models.PROTECT, null=True, blank=True)
    is_approved = models.BooleanField(default=False, blank=True)

    class Meta:
        default_permissions = ()
        permissions = []
